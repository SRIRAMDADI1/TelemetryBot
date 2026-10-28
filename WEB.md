# TelemetryBot — local run + public Azure deploy (**no Docker**)

Agent observability dashboard (Next.js) + collector API (FastAPI). Sign in, open a
tab per repo, and inspect token usage, cost, latency, and efficiency.

**Do not put API keys or OAuth secrets in this file.** Use `server/.env` locally, or
App Settings in Azure.

This guide deploys with **two Azure App Service apps** (Python collector + Node
dashboard) on **one Linux plan**, zip upload, and SQLite on the collector.
**Docker Desktop is not required.**

Google does **not** host the site. Azure serves HTTPS; [Google Search Console](https://search.google.com/search-console)
is how you **register the public URL as a website** so Google can index it (same
pattern as [sales-ivr/WEB.md](sales-ivr/WEB.md)).

---

## What gets deployed

| Azure resource | Purpose | Public URL |
|----------------|---------|------------|
| Resource group | Container for everything | — |
| App Service plan (Linux B1) | Shared compute | — |
| Web App **Python 3.12** | Collector API (`/health`, `/v1/...`) | `https://<api-name>.azurewebsites.net` |
| Web App **Node 20** | Dashboard UI (this is the Google website) | `https://<dash-name>.azurewebsites.net` |

SQLite lives on the collector at `/home/data/telemetrybot.db` (persists across
deploys). Postgres is optional later; local `docker compose` is not used here.

The **dashboard URL** is the site you share and register with Google. The collector
URL is the API (OAuth callbacks, ingest, query).

---

## Why zip deploy (not Compress-Archive)

PowerShell `Compress-Archive` stores entries like `app\main.py` (backslashes).
Azure App Service runs **Linux**. Unzip/Oryx then often **does not** create a real
`app/` package directory. Gunicorn starts, then dies:

```text
ModuleNotFoundError: No module named 'app'
```

**Fix:** always build zips with the pack scripts (forward-slash paths). Never use
`Compress-Archive` for this deploy.

- Collector: `python .\server\pack_azure_zip.py`
- Dashboard: `python .\dashboard\pack_azure_zip.py`

Python Oryx also extracts to `/tmp/...` and leaves `PYTHONPATH` pointing only at
`antenv`. `server/startup.sh` derives `APP_ROOT` from the live venv and runs
gunicorn with `--pythonpath` set to that root (same fix as sales-ivr).

---

## Part A — Run on your PC (optional)

```powershell
cd C:\Users\sd190\OneDrive\Documents\GitHub\TelemetryBot

# Collector
cd server
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8100
```

In a second window:

```powershell
cd C:\Users\sd190\OneDrive\Documents\GitHub\TelemetryBot\dashboard
npm install
npm run dev
```

Open http://localhost:3000 → sign in with `demo@telemetrybot.dev` / `demo`.

---

## Part B — Public site on Azure (no Docker)

Use **one** PowerShell window. Run sections in order.

### What you need

1. [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli-windows) (`az version`)
2. An Azure subscription
3. **Not** Docker Desktop
4. Python 3.11+ on the PC (only to run the pack scripts)

### B1. Install Azure CLI (once)

1. Install: https://learn.microsoft.com/cli/azure/install-azure-cli-windows
2. Open a **new** PowerShell window
3. Check:

```powershell
az version
```

---

### B2. Login and pick subscription

If `az` says the refresh token expired, run `az login` again before anything else.

```powershell
az login
az account list -o table
az account set --subscription "<PASTE-SUBSCRIPTION-ID>"
az account show -o table
```

---

### B3. Set names (edit, then keep this window open)

Web app names must be **globally unique** (they become `https://NAME.azurewebsites.net`).

```powershell
$SubscriptionId = "<PASTE-SUBSCRIPTION-ID>"
$Location       = "eastus"
$ResourceGroup  = "rg-telemetrybot"
$PlanName       = "telemetrybot-plan"
$ApiAppName     = "telemetrybot-api-sd190"    # change if taken
$DashAppName    = "telemetrybot-dash-sd190"   # change if taken — this is the Google website

$ApiUrl  = "https://$ApiAppName.azurewebsites.net"
$DashUrl = "https://$DashAppName.azurewebsites.net"

# Optional: real GitHub OAuth (leave empty to keep email + demo login)
$GitHubClientId     = ""
$GitHubClientSecret = ""
```

---

### B4. Go to the repo root

```powershell
cd C:\Users\sd190\OneDrive\Documents\GitHub\TelemetryBot
dir server\asgi.py, server\pack_azure_zip.py, server\startup.sh, server\requirements.txt, dashboard\pack_azure_zip.py, dashboard\startup.sh
```

---

### B5. Register App Service provider (first-time subscriptions)

```powershell
az provider register --namespace Microsoft.Web
do {
  Start-Sleep -Seconds 10
  $state = az provider show -n Microsoft.Web --query registrationState -o tsv
  Write-Host "Microsoft.Web = $state"
} while ($state -ne "Registered")
```

---

### B6. Create resource group + Linux plan + two Web Apps

Skip `az group create` / `az appservice plan create` if they already exist.

```powershell
az group create --name $ResourceGroup --location $Location

az appservice plan create `
  --name $PlanName `
  --resource-group $ResourceGroup `
  --is-linux `
  --sku B1

az webapp create `
  --name $ApiAppName `
  --resource-group $ResourceGroup `
  --plan $PlanName `
  --runtime "PYTHON:3.12"

az webapp create `
  --name $DashAppName `
  --resource-group $ResourceGroup `
  --plan $PlanName `
  --runtime "NODE:20-lts"
```

If a name is taken, change `$ApiAppName` / `$DashAppName`, recompute `$ApiUrl` /
`$DashUrl`, and re-run only the matching `az webapp create`.

---

### B7. Configure collector (Python)

```powershell
az webapp config set `
  --name $ApiAppName `
  --resource-group $ResourceGroup `
  --startup-file "startup.sh"

$apiSettings = @(
  "SCM_DO_BUILD_DURING_DEPLOYMENT=true"
  "ENABLE_ORYX_BUILD=true"
  "WEBSITES_PORT=8000"
  "DATABASE_URL=sqlite:////home/data/telemetrybot.db"
  "SEED_ON_STARTUP=true"
  "AUTH_DEV_MODE=false"
  "COLLECTOR_PUBLIC_URL=$ApiUrl"
  "DASHBOARD_URL=$DashUrl"
  "DEMO_EMAIL=demo@telemetrybot.dev"
  "DEMO_PASSWORD=demo"
)
if ($GitHubClientId -and $GitHubClientSecret) {
  $apiSettings += "GITHUB_CLIENT_ID=$GitHubClientId"
  $apiSettings += "GITHUB_CLIENT_SECRET=$GitHubClientSecret"
}

az webapp config appsettings set `
  --name $ApiAppName `
  --resource-group $ResourceGroup `
  --settings $apiSettings
```

`AUTH_DEV_MODE=false` on a public site so visitors cannot use mock GitHub.
Email + the seeded demo account still work. For real **Sign in with GitHub**, fill
`$GitHubClientId` / `$GitHubClientSecret` and complete Part D.

---

### B8. Configure dashboard (Node)

`NEXT_PUBLIC_COLLECTOR_URL` is baked in at **build** time. Set it **before** the
first dashboard deploy. If you change the collector URL later, redeploy the
dashboard (Part E) so Oryx rebuilds.

```powershell
az webapp config set `
  --name $DashAppName `
  --resource-group $ResourceGroup `
  --startup-file "startup.sh"

az webapp config appsettings set `
  --name $DashAppName `
  --resource-group $ResourceGroup `
  --settings `
    "SCM_DO_BUILD_DURING_DEPLOYMENT=true" `
    "ENABLE_ORYX_BUILD=true" `
    "WEBSITES_PORT=3000" `
    "NPM_CONFIG_PRODUCTION=false" `
    "NEXT_TELEMETRY_DISABLED=1" `
    "COLLECTOR_URL=$ApiUrl" `
    "NEXT_PUBLIC_COLLECTOR_URL=$ApiUrl"
```

`NPM_CONFIG_PRODUCTION=false` is required so Oryx installs TypeScript / Tailwind
(devDependencies) and can run `npm run build`.

---

### B9. Point the sitemap at the public dashboard URL

Edit `dashboard/public/sitemap.xml` and replace **both**
`REPLACE_WITH_YOUR_PUBLIC_URL` placeholders with `$DashUrl` (no trailing slash),
for example `https://telemetrybot-dash-sd190.azurewebsites.net`.

---

### B10. Stop both sites, build Linux-safe zips, deploy

Stopping first avoids Azure’s crash-loop / “site blocked” while you upload.

```powershell
cd C:\Users\sd190\OneDrive\Documents\GitHub\TelemetryBot

az webapp stop --name $ApiAppName --resource-group $ResourceGroup
az webapp stop --name $DashAppName --resource-group $ResourceGroup

# REQUIRED: Linux-safe zips (forward slashes). Do NOT use Compress-Archive.
python .\server\pack_azure_zip.py
python .\dashboard\pack_azure_zip.py

az webapp deploy `
  --name $ApiAppName `
  --resource-group $ResourceGroup `
  --src-path .\telemetrybot-collector-deploy.zip `
  --type zip

az webapp deploy `
  --name $DashAppName `
  --resource-group $ResourceGroup `
  --src-path .\telemetrybot-dashboard-deploy.zip `
  --type zip
```

First deploy (and any deploy that reinstalls wheels/node_modules) can take
**5–15 minutes per app** while Oryx runs `pip install` / `npm install` +
`next build`. Wait until each `az webapp deploy` prints success. Do not
health-check mid-deploy.

---

### B11. Start the sites and open the dashboard

```powershell
# If Azure previously blocked cold starts, wait out the block window
Start-Sleep -Seconds 130

az webapp start --name $ApiAppName --resource-group $ResourceGroup
az webapp start --name $DashAppName --resource-group $ResourceGroup

Write-Host "Collector: $ApiUrl/health"
Write-Host "Dashboard: $DashUrl"
Write-Host "Login:     $DashUrl/login"

# Cold start + Oryx extract often needs a minute
Start-Sleep -Seconds 90
Start-Process $DashUrl
```

---

### B12. Verify

```powershell
Invoke-RestMethod "$ApiUrl/health"
Invoke-WebRequest "$DashUrl/login" | Select-Object StatusCode, StatusDescription
Invoke-WebRequest "$DashUrl/sitemap.xml" | Select-Object StatusCode
Invoke-WebRequest "$DashUrl/robots.txt" | Select-Object StatusCode
```

Expected collector:

```json
{"status":"ok"}
```

Dashboard `/login` should be **200**. Sign in with:

| | |
|--|--|
| Email | `demo@telemetrybot.dev` |
| Password | `demo` |

If the collector fails:

```powershell
az webapp log startup show --name $ApiAppName --resource-group $ResourceGroup
```

Look for:

- `TelemetryBot collector startup: APP_ROOT=/tmp/...` (good)
- `cannot import app.main` or `ModuleNotFoundError` (bad — usually means B10 used
  `Compress-Archive` or an old zip)

If the dashboard fails:

```powershell
az webapp log startup show --name $DashAppName --resource-group $ResourceGroup
```

Look for:

- `TelemetryBot dashboard startup: APP_ROOT=/home/site/wwwroot` (good)
- `.next missing` (bad — Oryx did not build; check `NPM_CONFIG_PRODUCTION=false`
  and that `package.json` is at the zip root)
- `Collector unreachable` in the browser (dashboard built with the wrong
  `NEXT_PUBLIC_COLLECTOR_URL`, or the collector is down)

---

## Part C — Register as a Google website (Search Console)

This is the same step as sales-ivr “Google Search”: Azure already hosts the HTTPS
site; Google only **indexes** it.

The property you add is the **dashboard** URL (`$DashUrl`), not the collector.

### C1. Confirm the public pages

Google can fetch:

- `https://<dash-name>.azurewebsites.net/` (redirects to `/login` when signed out)
- `https://<dash-name>.azurewebsites.net/login`
- `https://<dash-name>.azurewebsites.net/sitemap.xml`
- `https://<dash-name>.azurewebsites.net/robots.txt`

Signed-in app routes (`/p/...`, `/connect`) are disallowed in `robots.txt`.

### C2. Add the property

1. Open [Google Search Console](https://search.google.com/search-console).
2. **Add property** → **URL prefix** → paste `$DashUrl` (with `https://`, no path).
3. Choose **HTML file** verification (simplest on App Service).

### C3. Upload the verification file and redeploy

1. Download the `google*.html` file Search Console gives you.
2. Copy it into `dashboard/public/` (same folder as `sitemap.xml`).
3. Redeploy **only the dashboard** (Part E).
4. In Search Console, click **Verify**.

HTML-file verification is public on purpose (`https://<dash>/google….html`). Do not
put secrets in that file.

### C4. Submit the sitemap

1. Search Console → **Sitemaps**.
2. Submit `sitemap.xml`.
3. Use **URL Inspection** on `$DashUrl/login` → **Request indexing** (optional).

Indexing can take **days/weeks**. The Azure URL is shareable immediately; Google
does not have to finish indexing first.

### C5. Optional custom domain

Portal → dashboard Web App → **Custom domains** → add `www.example.com` (or similar)
→ then add a **new** Search Console property for that domain (DNS TXT or HTML file).

---

## Part D — (Optional) GitHub sign-in (OAuth app)

Search Console (Part C) does **not** enable the dashboard’s **Continue with GitHub**
button. That needs a GitHub **OAuth App**.

1. GitHub → **Settings** → **Developer settings** → **OAuth Apps** → **New OAuth App**.
2. Authorization callback URL (must match exactly):
   - `$ApiUrl/v1/auth/github/callback`
3. Copy Client ID and Client secret into `$GitHubClientId` / `$GitHubClientSecret`
   (or set them in Portal → collector Web App → Configuration).
4. Restart the collector:

```powershell
az webapp config appsettings set `
  --name $ApiAppName `
  --resource-group $ResourceGroup `
  --settings `
    "GITHUB_CLIENT_ID=<id>" `
    "GITHUB_CLIENT_SECRET=<secret>" `
    "AUTH_DEV_MODE=false"

az webapp restart --name $ApiAppName --resource-group $ResourceGroup
```

---

## Part E — Redeploy after code changes

Keep the same `$ApiAppName`, `$DashAppName`, `$ResourceGroup` as Part B.

```powershell
cd C:\Users\sd190\OneDrive\Documents\GitHub\TelemetryBot
$ApiAppName    = "telemetrybot-api-sd190"
$DashAppName   = "telemetrybot-dash-sd190"
$ResourceGroup = "rg-telemetrybot"

az webapp stop --name $ApiAppName --resource-group $ResourceGroup
az webapp stop --name $DashAppName --resource-group $ResourceGroup

python .\server\pack_azure_zip.py
python .\dashboard\pack_azure_zip.py

az webapp deploy `
  --name $ApiAppName `
  --resource-group $ResourceGroup `
  --src-path .\telemetrybot-collector-deploy.zip `
  --type zip

az webapp deploy `
  --name $DashAppName `
  --resource-group $ResourceGroup `
  --src-path .\telemetrybot-dashboard-deploy.zip `
  --type zip

Start-Sleep -Seconds 130
az webapp start --name $ApiAppName --resource-group $ResourceGroup
az webapp start --name $DashAppName --resource-group $ResourceGroup
Start-Sleep -Seconds 90
Invoke-RestMethod "https://$ApiAppName.azurewebsites.net/health"
```

Dashboard-only (sitemap, `google*.html`, UI):

```powershell
python .\dashboard\pack_azure_zip.py
az webapp stop --name $DashAppName --resource-group $ResourceGroup
az webapp deploy --name $DashAppName --resource-group $ResourceGroup --src-path .\telemetrybot-dashboard-deploy.zip --type zip
Start-Sleep -Seconds 90
az webapp start --name $DashAppName --resource-group $ResourceGroup
```

---

## Part F — Tear down (stop billing)

```powershell
az group delete --name rg-telemetrybot --yes --no-wait
```

This deletes both web apps, the plan, and the SQLite file.

---

## Part G — Temporary demo URL only (not for Google)

With the local dashboard already running on port 3000 **and** the collector on 8100:

```powershell
npx localtunnel --port 3000
```

Do not submit a localtunnel URL to Search Console (it expires and is not a stable
website).

---

## Checklist

| Step | Required? |
|------|-----------|
| Azure CLI | Yes |
| Docker Desktop | **No** |
| `python .\server\pack_azure_zip.py` (not Compress-Archive) | **Yes** for every collector deploy |
| `python .\dashboard\pack_azure_zip.py` (not Compress-Archive) | **Yes** for every dashboard deploy |
| Part B deploy | Yes for a public HTTPS site |
| Edit `dashboard/public/sitemap.xml` | Yes before Google registration |
| Google Search Console (Part C) | Yes to register as a Google website |
| GitHub OAuth app (Part D) | Optional (email/demo login works without it) |

---

## After it is live

| What | URL |
|------|-----|
| Dashboard (Google website) | `https://<dash-name>.azurewebsites.net` |
| Login | `https://<dash-name>.azurewebsites.net/login` |
| Collector health | `https://<api-name>.azurewebsites.net/health` |
| Collector OpenAPI | `https://<api-name>.azurewebsites.net/docs` |
| Sitemap | `https://<dash-name>.azurewebsites.net/sitemap.xml` |

Demo login: `demo@telemetrybot.dev` / `demo`.

Workloads (Sales IVR, CLI ingest) should send traces to the **collector** with
`X-API-Key` (the project ingest key from dashboard Settings), not to the dashboard:

```powershell
$env:TELEMETRY_API_KEY = "<ingest key from Settings>"
$env:TELEMETRY_ENDPOINT = "https://<api-name>.azurewebsites.net/v1/ingest"
```

See [README.md](README.md) for local SDK / CLI usage.
