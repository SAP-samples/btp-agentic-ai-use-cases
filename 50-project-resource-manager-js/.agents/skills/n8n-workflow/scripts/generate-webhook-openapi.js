#!/usr/bin/env node

/**
 * Outputs a valid OpenAPI 3.0 spec (JSON, to stdout) for every webhook node
 * found in an n8n workflow file.
 *
 * Usage:
 *   node generate-webhook-openapi.js <workflow-file> <workflow-name>
 *
 * Each webhook node becomes one path entry in the spec.  When multiple webhook
 * nodes are present their paths are merged into a single spec document.
 *
 * Outputs an empty object `{}` and exits 0 when the workflow has no webhook
 * nodes (signals to the caller that the MCP-server step can be skipped).
 */

import { readFileSync } from "node:fs";

const [, , file, workflowName] = process.argv;

if (!file || !workflowName) {
  console.error("Usage: node generate-webhook-openapi.js <workflow-file> <workflow-name>");
  process.exit(1);
}

let wf;
try {
  wf = JSON.parse(readFileSync(file, "utf-8"));
} catch (error) {
  console.error(`Failed to parse workflow JSON from ${file}: ${error.message}`);
  process.exit(1);
}

if (!Array.isArray(wf.nodes)) {
  console.error(`Invalid workflow format in ${file}: expected a 'nodes' array.`);
  process.exit(1);
}

const webhookNodes = wf.nodes.filter((node) => node.type === "n8n-nodes-base.webhook");

// No webhook nodes — output empty object so the caller can skip the MCP step.
if (webhookNodes.length === 0) {
  process.stdout.write("{}\n");
  process.exit(0);
}

// ── helpers ──────────────────────────────────────────────────────────────────

/**
 * Splits a string on non-alphanumeric runs and filters empty tokens.
 */
function normalizeWords(str) {
  return String(str)
    .trim()
    .split(/[^a-zA-Z0-9]+/)
    .filter(Boolean);
}

/**
 * Converts a string to camelCase — matches the convention used by
 * generate-workflow-asset.js so that operationIds align with the apiName
 * segment of the REST ORD ID (ADR-021 §8.1 tool-name convention).
 */
function toCamel(str) {
  const words = normalizeWords(str);
  if (words.length === 0) return "";
  return (
    words[0].toLowerCase() +
    words
      .slice(1)
      .map((w) => w[0].toUpperCase() + w.slice(1).toLowerCase())
      .join("")
  );
}

// ── generateWebhookOpenApiSpec ────────────────────────────────────────────────

/**
 * Generate OpenAPI 3.0 specification for a webhook endpoint
 *
 * Per ORD spec, REST APIs should have an OpenAPI spec in resourceDefinitions.
 * This generates a minimal OpenAPI 3.0.0 spec for the webhook.
 *
 * n8n webhooks specify their HTTP method in the node's parameters.httpMethod field.
 * If provided, we generate spec for that specific method. Otherwise, we include
 * all common methods since n8n webhook triggers can be configured for any method.
 *
 * @param {Object} tenant - Workflow tenant object
 * @param {Object} webhook - Webhook object
 * @param {string} [webhook.httpMethod] - HTTP method from n8n webhook node (e.g., "POST", "GET")
 * @param {string[]} [webhook.methods] - Array of HTTP methods (alternative to httpMethod)
 * @returns {Object} OpenAPI 3.0.0 specification
 */
function generateWebhookOpenApiSpec(tenant, webhook) {
  const webhookPathClean = `/${webhook.path.replace(/^\//, "")}`;

  // Determine supported HTTP methods:
  // 1. If webhook.httpMethod is set (from n8n node), use only that method
  // 2. If webhook.methods array is set, use those
  // 3. Otherwise, include all common methods
  let supportedMethods;
  if (webhook.httpMethod) {
    // Single method from n8n webhook node configuration
    supportedMethods = [webhook.httpMethod.trim().toLowerCase()];
  } else if (webhook.methods && Array.isArray(webhook.methods)) {
    supportedMethods = webhook.methods.map((m) => m.toLowerCase());
  } else {
    // Default to common methods if not specified
    supportedMethods = ["get", "post", "put", "delete", "patch"];
  }

  // Build operations for each HTTP method
  const pathOperations = {};

  // Common response schema
  const successResponse = {
    description: "Webhook executed successfully",
    content: {
      "application/json": {
        schema: {
          type: "object",
          additionalProperties: true,
          description: "Response from workflow execution",
        },
      },
    },
  };

  const errorResponses = {
    401: { description: "Unauthorized - Invalid or missing JWT token" },
    403: { description: "Forbidden - Token audience mismatch or invalid issuer" },
    500: { description: "Internal Server Error - Workflow execution failed" },
  };

  // Common request body schema (for methods that accept body)
  const requestBody = {
    description: "Webhook payload - passed to workflow as input",
    required: false,
    content: {
      "application/json": {
        schema: {
          type: "object",
          additionalProperties: true,
          description: "JSON payload for the workflow",
        },
      },
      "application/x-www-form-urlencoded": {
        schema: {
          type: "object",
          additionalProperties: true,
        },
      },
      "multipart/form-data": {
        schema: {
          type: "object",
          additionalProperties: true,
        },
      },
    },
  };

  // Methods that accept request body
  const methodsWithBody = ["post", "put", "patch"];

  for (const method of supportedMethods) {
    const methodLower = method.toLowerCase();
    const methodUpper = method.toUpperCase();

    pathOperations[methodLower] = {
      summary: `${methodUpper} ${webhook.name || webhook.path}`,
      description: `${methodUpper} endpoint for webhook: ${webhook.path}\n\nWorkflow: ${tenant.workflowName || tenant.tenantName}`,
      // operationId follows ADR-021 §8.1 tool-name convention: camelCase of the
      // webhook node name (= apiName segment of the REST ORD ID).
      // When multiple HTTP methods are generated for the same webhook, prefix
      // with the method to keep operationIds unique within the spec.
      operationId:
        supportedMethods.length === 1
          ? toCamel(webhook.name || webhook.path)
          : toCamel(`${methodUpper} ${webhook.name || webhook.path}`),
      tags: [tenant.workflowName || tenant.tenantName],
      responses: {
        200: successResponse,
        ...errorResponses,
      },
      security: [{ bearerAuth: [] }],
    };

    // Add request body for methods that support it
    if (methodsWithBody.includes(methodLower)) {
      pathOperations[methodLower].requestBody = requestBody;
    }

    // Add query parameters for GET
    if (methodLower === "get") {
      pathOperations[methodLower].parameters = [
        {
          name: "query",
          in: "query",
          description: "Query parameters are passed to the workflow",
          required: false,
          schema: {
            type: "object",
            additionalProperties: true,
          },
          style: "form",
          explode: true,
        },
      ];
    }
  }

  return {
    openapi: "3.0.3",
    info: {
      title: webhook.name || `${tenant.workflowName} - ${webhook.path}`,
      description: [
        `Webhook endpoint for workflow tenant: ${tenant.tenantName}`,
        ``,
        `**Workflow:** ${tenant.workflowName || "N/A"}`,
        ``,
        `This webhook accepts multiple HTTP methods. The request body/query parameters`,
        `are passed as input to the n8n workflow execution.`,
      ].join("\n"),
      version: tenant.versionId || "1.0.0",
      contact: {
        name: "Managed n8n Support",
      },
    },
    servers: [
      {
        url: tenant.tenantUrl,
        description: "Workflow tenant webhook base URL",
      },
    ],
    tags: [
      {
        name: tenant.workflowName || tenant.tenantName,
        description: `Webhooks for workflow: ${tenant.workflowName || tenant.tenantName}`,
      },
    ],
    paths: {
      [webhookPathClean]: pathOperations,
    },
    components: {
      securitySchemes: {
        bearerAuth: {
          type: "http",
          scheme: "bearer",
          bearerFormat: "JWT",
          description:
            "JWT token with correct issuer and audience for this workflow tenant. Token is validated by Istio RequestAuthentication.",
        },
      },
    },
  };
}

// ── build combined spec from all webhook nodes ────────────────────────────────

const tenant = {
  tenantName: workflowName,
  workflowName,
  // Placeholder URL — the real base URL is resolved at deployment time.
  tenantUrl: "https://your-n8n-workflow-tenant.example.com",
  versionId: "1.0.0",
};

// Accumulate paths across all webhook nodes, then build a single spec envelope.
// Using a Map lets us deep-merge per-path method objects instead of overwriting
// them (which Object.assign would do when two nodes share the same URL path).
const accumulatedPaths = new Map();
const seenOperationIds = new Set();
let firstSpec = null;

for (const node of webhookNodes) {
  const rawPath = String(node.parameters?.path ?? "").trim();
  if (!rawPath) {
    console.error(
      `Webhook node '${node.name}' is missing parameters.path; cannot generate path entry.`,
    );
    process.exit(1);
  }

  const webhook = {
    path: rawPath,
    name: node.name,
    // n8n stores the selected HTTP method in parameters.httpMethod (optional).
    httpMethod: node.parameters?.httpMethod ?? undefined,
  };

  const spec = generateWebhookOpenApiSpec(tenant, webhook);

  // Capture the envelope from the first spec only.
  if (firstSpec === null) firstSpec = spec;

  for (const [pathKey, methodsObj] of Object.entries(spec.paths)) {
    const existing = accumulatedPaths.get(pathKey) ?? {};

    for (const [method, operation] of Object.entries(methodsObj)) {
      let opId = operation.operationId;
      if (seenOperationIds.has(opId)) {
        let suffix = 2;
        while (seenOperationIds.has(`${opId}${suffix}`)) suffix++;
        opId = `${opId}${suffix}`;
        operation.operationId = opId;
      }
      seenOperationIds.add(opId);

      existing[method] = operation;
    }

    accumulatedPaths.set(pathKey, existing);
  }
}

// Build the final spec from the first envelope plus the merged paths.
const combinedSpec = {
  ...firstSpec,
  paths: Object.fromEntries(accumulatedPaths),
};

process.stdout.write(`${JSON.stringify(combinedSpec, null, 2)}\n`);
