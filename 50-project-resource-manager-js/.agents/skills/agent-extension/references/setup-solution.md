### Workflow
While  **Creating appropriate structure inside `assets/`** in point 4 of the workflow:
   - For `agent-extension` assets: create `asset.yaml` and `extension.yaml`. The `asset.yaml` MUST include a `requires` entry with `type: agent` referencing the base agent's `ordId` and `version` (see Example Agent Extension Asset)
**Create appropriate structure inside `assets/`**:

### Examples
#### Example 1: Agent Extension Asset
```yaml
apiVersion: asset.sap/v1
kind: Asset

metadata:
  name: employee-onboarding-tools
  version: 1.0.0

type: agent-extension

sourceRoot: "."

provides:
  extensions:
    - descriptorFile: extension.yaml
      name: employee-onboarding-tools

requires:
  - name: employee-onboarding-agent
    type: agent
    version: "1.0.0"
    ordId: customer.build:agent:employee-onboarding.employee-onboarding-agent:v1
```

The agent extension asset folder contains `asset.yaml` and `extension.yaml`:
```
assets/employee-onboarding-tools/
├── asset.yaml          # as above - MUST include requires with agent reference
└── extension.yaml      # extension descriptor (tools, hooks, instructions)
```

**CRITICAL**: The `requires` array MUST include at least one entry with `type: agent` referencing the base agent's `ordId` and `version`. Without this, the platform cannot resolve the agent dependency.
