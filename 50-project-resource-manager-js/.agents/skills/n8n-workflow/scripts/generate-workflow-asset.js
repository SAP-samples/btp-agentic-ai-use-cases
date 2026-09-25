#!/usr/bin/env node

/**
 * Outputs the top-level workflow: block and provides.apis[] YAML for asset.yaml.
 *
 * Usage:
 *   node generate-workflow-asset.js <workflow-file> <workflow-name> <solution-name>
 *
 * Each webhook node produces two provides.apis[] entries:
 *   - kind: rest  — the HTTP endpoint
 *   - kind: mcp-server — the MCP translation entry
 *
 * The webhook path is composed at design time as <solution-name>/<workflow-name>/<operation>,
 * where <operation> is derived from the webhook node's name (same source as the
 * API name and ORD IDs, so the path always fits the ordId). It is written back
 * into the node's parameters.path (no leading slash) and emitted as the kind:
 * rest path (with leading slash), so no webhook URL is generated at deploy time.
 * Re-running is idempotent.
 *
 * The LLM must paste the output verbatim into asset.yaml and fill in the
 * description placeholder on each kind: rest entry.
 */

import { readFileSync, writeFileSync } from "node:fs";
import { basename } from "node:path";

const [, , file, workflowName, solutionName] = process.argv;

if (!file || !workflowName || !solutionName) {
  console.error(
    "Usage: node generate-workflow-asset.js <workflow-file> <workflow-name> <solution-name>",
  );
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

// Quote a YAML scalar only when it contains characters that would break bare style
function yamlString(value) {
  const s = String(value);
  return /[:#[\]{},&*?|<>=!%@`"']|^\s|\s$/.test(s) ? JSON.stringify(s) : s;
}

function normalizeWords(str) {
  return String(str)
    .trim()
    .split(/[^a-zA-Z0-9]+/)
    .filter(Boolean);
}

/** Convert a string to snake_case */
function toSnake(str) {
  return normalizeWords(str)
    .map((word) => word.toLowerCase())
    .join("_");
}

/** Convert a string to camelCase (lowercase first letter) */
function toCamel(str) {
  const words = normalizeWords(str);
  if (words.length === 0) return "";
  return (
    words[0].toLowerCase() +
    words
      .slice(1)
      .map((word) => word[0].toUpperCase() + word.slice(1).toLowerCase())
      .join("")
  );
}

const definitionFile = basename(file);

// ── workflow: block ─────────────────────────────────────────────────────────
let yaml = `workflow:\n`;
yaml += `  definitionFile: ${yamlString(definitionFile)}\n`;
yaml += `  name: ${yamlString(workflowName)}\n`;
yaml += `  ordId: sap.btpn8n:apiResource:ManagedN8nMcpServer:v1\n`;

if (webhookNodes.length === 0) {
  process.stdout.write(`${yaml.trimEnd()}\n`);
  process.exit(0);
}

// ── provides.apis[] block ────────────────────────────────────────────────────
const seenNames = new Set();
const seenOrdIds = new Set();

const apis = [];
let workflowModified = false;

webhookNodes.forEach((n) => {
  const snake = toSnake(n.name);
  const camel = toCamel(n.name);

  if (!snake || !camel) {
    console.error(`Unable to derive API identifiers from node name: '${n.name}'`);
    process.exit(1);
  }

  const mcpCamel = `${camel}McpServer`;
  const mcpSnake = `${snake}_mcp_server`;

  // Full design-time webhook path: <solution-name>/<asset-name>/<operation>.
  // The operation segment is derived from the node name (kebab-case == the API
  // name with "-"), the same source as the API name and ORD IDs, so the path
  // always fits the ordId. <asset-name> is the workflow name (== asset
  // metadata.name by convention). The runtime appends this to the tenant URL
  // as-is, so no webhook URL is generated at deploy time.
  const operation = snake.replace(/_/g, "-");
  const nodePath = `${solutionName}/${workflowName}/${operation}`;
  const path = `/${nodePath}`;
  n.parameters = n.parameters ?? {};
  if (n.parameters.path !== nodePath) {
    n.parameters.path = nodePath;
    workflowModified = true;
  }

  const restOrdId = `sap.n8nwfrt:apiResource:${solutionName}_${workflowName}.${camel}:v1`;
  const mcpOrdId = `sap.n8nwfrt:apiResource:${solutionName}_${workflowName}.${mcpCamel}:v1`;

  for (const id of [restOrdId, mcpOrdId]) {
    if (seenOrdIds.has(id)) {
      console.error(`Duplicate ORD ID generated: '${id}' (from node name '${n.name}')`);
      process.exit(1);
    }
    seenOrdIds.add(id);
  }

  if (seenNames.has(snake) || seenNames.has(mcpSnake)) {
    console.error(`Duplicate API name generated for node name: '${n.name}'`);
    process.exit(1);
  }
  seenNames.add(snake);
  seenNames.add(mcpSnake);

  apis.push({
    name: snake,
    path,
    kind: "rest",
    ordId: restOrdId,
    displayName: n.name,
  });
  apis.push({
    name: mcpSnake,
    kind: "mcp-server",
    displayName: n.name,
    ordId: mcpOrdId,
  });
});

yaml += `\nprovides:\n  apis:\n`;
apis.forEach((a) => {
  yaml += `    - name: ${yamlString(a.name)}\n`;
  if (a.kind === "rest") {
    yaml += `      path: ${yamlString(a.path)}\n`;
  }
  yaml += `      kind: ${a.kind}\n`;
  if (a.kind === "rest") {
    yaml += `      description: <add description>\n`;
  } else {
    yaml += `      description: MCP server for ${a.displayName.toLowerCase()} operations\n`;
  }
  yaml += `      ordId: ${yamlString(a.ordId)}\n`;
});

if (workflowModified) {
  writeFileSync(file, `${JSON.stringify(wf, null, 2)}\n`);
}

process.stdout.write(`${yaml.trimEnd()}\n`);
