---
name: joule-studio-cli
description: Use this skill as a helper to the `deploy-solution` skill to assist the user in deploying a solution via joule-studio-cli. This skill should only be used when the tools mentioned in 'deploy-solution' skill are not found.
compatibility: Requires jl >= 0.1.20-alpha.12
metadata:
  version: 1.1.0
  author: sap-joule-studio
---

# Validate, Build and deploy a solution with joule-studio-cli

## Prerequisites
- `@sap/joule-work-dev-cli-early-adopters` CLI, referred to as joule-studio-cli, must be installed. Do not attempt to install it.
- Only use when `deploy_solution` tool is unavailable.

## Workflow

### Step 1: Login
1. Check whether the user is already authenticated:
   ```bash
   jl info
   ```
2. If the CLI is already logged in, continue to validation.
3. If the CLI is not logged in, ask the user for the login URL copied from the Joule Studio UI and run:
   ```bash
   jl login <login-url>
   ```
   If a login URL was previously stored, `jl login` can be run without arguments.

The login URL has the following format:
```
https://<backend-host>?issuerUrl=<ias-url>&clientId=<client-id>&appTid=<tenant-id>
```
The command opens a browser to complete an OAuth 2.0 PKCE flow. The URL is stored after first login.

### Step 2: Validate the solution
Prior to deployment, validate the solution configuration and assets:
```bash
jl solution validate
```

The solution is ready to deploy if the validation command responds with `Validation passed.`. If there are any validation errors, address them before proceeding.

### Step 3: Build the solution
Once the solution is validated, build the solution to prepare it for deployment:
```bash
jl solution build
```
The solution is built if the output contains `Archive created: <build-location>`. Keep the `build-location` for the next step.

### Step 4: Deploy the solution
After a successful build, the solution package can be deployed using the following command:
```bash
jl solution deploy <build-location>
```

### Step 5: Check Deployment Status
Check the deployment status using:
```bash
jl solution deploy status <solution_id>
```

### Step 6: Deployment result
Always store the result in `deploy_result.json` in the following format:

```json
{ "solution_id": "<some_uuid>" }
```
- Refer to the troubleshooting section in case of a failed deployment. Inform the user briefly of the cause of failure.


## Validation
If the deployed solution contains an agent asset, it can be tested by sending an A2A message once the solution is running:

```bash
jl a2a message "hi, how are you?" --solution <solution_id> --asset <agent_asset_name>
```

- `<solution_id>`: the UUID from `deploy_result.json`
- `<agent_asset_name>`: the name of the agent asset (as defined in `asset.yaml`).

Inform the user of this command after a successful deployment if the solution contains an agent asset.

## Troubleshooting

### Failed deployment
If the deployment fails, fetch the job logs:
```bash
jl solution deploy logs <solution_id> --job <job_id>
```

## Gotchas
- Do not confuse the `deploy-solution` **skill** with the `deploy_solution` **tool**. The tool is part of the skill. Notice the naming difference: the skill uses kebab-case while the tool uses snake_case.
