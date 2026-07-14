# Sales IVR (LLM agents)

Insurance sales IVR platform driven by **real LLM agents** (Azure OpenAI by default),
with tools for CRM, catalog, pricing, and compliance. Token usage is recorded on every
run for future TelemetryBot observability.

## Azure OpenAI setup (do this once)

### 1. Create an Azure OpenAI resource

1. Open [https://portal.azure.com](https://portal.azure.com) and sign in.
2. Click **Create a resource** → search **Azure OpenAI** → **Create**.
3. Fill in:
   - Subscription: your credit subscription
   - Resource group: create `rg-sales-ivr` (or any name)
   - Region: pick one that supports GPT-4o-mini (e.g. East US, Sweden Central)
   - Name: e.g. `sales-ivr-openai`
   - Pricing tier: Standard S0
4. **Review + create** → **Create**. Wait until deployment finishes.

> If you get "Request access": Azure OpenAI may still require a one-time access
> request for some subscriptions. Complete the form if prompted, then retry.

### 2. Deploy a model

1. Open your Azure OpenAI resource in the portal.
2. Click **Model deployments** / **Go to Azure AI Foundry** (or OpenAI Studio).
3. **Deploy model** → **Deploy base model**.
4. Choose **gpt-4o-mini** (cheap for demos) or **gpt-4o** (stronger).
5. Set **Deployment name** to `gpt-4o-mini` (must match `config.yaml` → `llm.deployment`).
6. Deploy.

### 3. Copy endpoint + API key

1. Back in the Azure portal → your OpenAI resource.
2. Left menu: **Keys and Endpoint**.
3. Copy:
   - **Endpoint** (e.g. `https://sales-ivr-openai.openai.azure.com/`)
   - **KEY 1**

### 4. Set environment variables (PowerShell)

```powershell
$env:AZURE_OPENAI_API_KEY = "<KEY 1>"
$env:AZURE_OPENAI_ENDPOINT = "https://your-resource-name.openai.azure.com/"
```

Then in `sales-ivr/config.yaml` set:

```yaml
llm:
  provider: "azure"
  deployment: "gpt-4o-mini"   # must match Azure deployment name
```

Do **not** commit the API key. Keep it in your shell / `.env` (gitignored).

### 5. Verify

```powershell
cd sales-ivr
pip install -e ".[dev]"
python -m sales_ivr.cli auto_quote_ca.json
```

You should see `llm_calls:` with real token counts.

## Offline / CI mode (no Azure)

`config.yaml` defaults to `provider: "mock"` so tests run without credentials:

```bash
python -m pytest
python -m sales_ivr.cli auto_quote_ca.json
```

## Quick start

```bash
cd sales-ivr
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
python -m pytest
python -m sales_ivr.cli auto_quote_ca.json
python -m sales_ivr.cli auto_quote_ca.json --json
python run_batch.py
```

## Architecture

Each of the 8 LangGraph nodes is an LLM agent that:

1. Receives session JSON context
2. Optionally calls tools (`lookup_crm`, `list_products`, `calculate_premium`, `load_compliance`, …)
3. Returns structured JSON applied to `IVRState`
4. Records `LLMUsage` (tokens, latency, tool_calls) on the state

## Input / output

**Input:** fixture JSON under `sales_ivr/fixtures/sessions/`  
**Output:** enriched `IVRState` with quote/handoff + `llm_usage[]`
