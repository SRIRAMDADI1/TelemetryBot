# ADO Agent Pipeline

Holds the Azure DevOps backlog for agent-building work and (later) the meta-agents
that implement the Sales IVR agents from those work items.

TelemetryBot registers this folder as the **ADO Pipeline** monitoring tab. Until
meta-agents exist, the tab stays empty (coverage scan only). Optional demo:

```bash
pip install -e ../packages/agentelemetry
python telemetry_smoke.py --demo-seed
```

Only **agent-building** work is tracked in Azure DevOps (Epics E2-E7). Platform
foundation (E1) lives in code under `sales-ivr/`.

## Files

- `backlog.py` — the backlog data (epics, features, user stories, tasks, acceptance criteria)
- `create_backlog.py` — creates the backlog in Azure DevOps via the REST API (stdlib only)

## What gets created

6 epics, 10 features, 23 user stories, 70 tasks. User stories are tagged
`agent-buildable` and carry acceptance criteria in the standard ADO field.

## Preview without an account

```bash
python create_backlog.py --dry-run
```

## One-time Azure DevOps setup

Azure DevOps (dev.azure.com) is separate from the Azure portal (portal.azure.com)
and does not consume Azure credits.

1. Create an organization: https://dev.azure.com -> "New organization" (sign in with your Microsoft account).
2. Create a project:
   - Name: `SalesIVRInsurance` (or your choice)
   - Visibility: Private
   - Advanced -> Work item process: **Agile**
3. Create a Personal Access Token (PAT):
   - User settings (top right) -> Personal access tokens -> New Token
   - Scopes: **Work Items (Read & Write)**
   - Copy the token (shown once)

## Run it

Set environment variables (PowerShell):

```powershell
$env:AZURE_DEVOPS_ORG_URL = "https://dev.azure.com/YourOrg"
$env:AZURE_DEVOPS_PROJECT = "SalesIVRInsurance"
$env:AZURE_DEVOPS_PAT     = "<your-pat>"
python create_backlog.py
```

The PAT is read from the environment and is never written to disk or committed.
