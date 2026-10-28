from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel

# Use isolated sqlite DB for tests (process env wins over server/.env)
os.environ["DATABASE_URL"] = "sqlite:///./test_telemetrybot.db"
os.environ["SEED_ON_STARTUP"] = "true"
os.environ["AUTH_DEV_MODE"] = "true"
os.environ["GITHUB_CLIENT_ID"] = ""
os.environ["GITHUB_CLIENT_SECRET"] = ""

from app.db.session import get_engine, reset_engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services.seed import seed_system_projects  # noqa: E402
from app.settings import clear_settings_cache  # noqa: E402

clear_settings_cache()


@pytest.fixture(autouse=True)
def _fresh_db():
    reset_engine()
    clear_settings_cache()
    engine = get_engine()
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    seed_system_projects()
    yield
    reset_engine()
    if os.path.exists("test_telemetrybot.db"):
        os.remove("test_telemetrybot.db")


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers(client: TestClient):
    resp = client.post(
        "/v1/auth/email/login",
        json={"email": "demo@telemetrybot.dev", "password": "demo"},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["session_token"]
    return {"Authorization": f"Bearer {token}"}


def test_dashboard_finish_rejects_absolute_redirects():
    from app.api.auth import _dashboard_finish, _safe_dashboard_path

    assert _safe_dashboard_path("/auth/callback?next=/p/x") == "/auth/callback?next=/p/x"
    assert _safe_dashboard_path("https://evil.example") == "/auth/callback"
    assert _safe_dashboard_path("//evil.example") == "/auth/callback"
    location = _dashboard_finish("tok", "https://evil.example/phish").headers["location"]
    assert "evil" not in location
    assert "token=tok" in location


def test_health(client: TestClient):
    assert client.get("/health").json()["status"] == "ok"


def test_projects_require_auth(client: TestClient):
    assert client.get("/v1/projects").status_code == 401


def test_demo_login_sees_system_projects(client: TestClient, auth_headers: dict):
    projects = client.get("/v1/projects", headers=auth_headers).json()
    slugs = [p["slug"] for p in projects]
    assert "sales-ivr" in slugs
    assert "ado-pipeline" in slugs
    # Sales IVR is the primary demo tab and should lead the tab strip.
    assert slugs.index("sales-ivr") < slugs.index("ado-pipeline")


def test_me_and_logout(client: TestClient, auth_headers: dict):
    me = client.get("/v1/auth/me", headers=auth_headers).json()["user"]
    assert me["email"] == "demo@telemetrybot.dev"
    assert me["is_demo"] is True
    assert client.post("/v1/auth/logout", headers=auth_headers).json()["ok"] is True
    assert client.get("/v1/auth/me", headers=auth_headers).status_code == 401


def test_magic_link_login(client: TestClient):
    req = client.post("/v1/auth/email/magic", json={"email": "newuser@example.com"})
    assert req.status_code == 200
    token = req.json()["dev_token"]
    verify = client.post("/v1/auth/email/magic/verify", json={"token": token})
    assert verify.status_code == 200
    headers = {"Authorization": f"Bearer {verify.json()['session_token']}"}
    projects = client.get("/v1/projects", headers=headers).json()
    assert projects == []


def test_dev_github_connect_and_import(client: TestClient, auth_headers: dict):
    # Mock GitHub connect is only allowed for the seeded demo account
    gh = client.post("/v1/auth/dev/github", headers=auth_headers, json={})
    assert gh.status_code == 200
    headers = {"Authorization": f"Bearer {gh.json()['session_token']}"}
    assert gh.json()["user"]["github_connected"] is True
    assert gh.json()["user"]["github_login"] == "octocat-dev"

    repos = client.get("/v1/github/repos", headers=headers).json()
    assert repos["source"] == "dev"
    assert len(repos["repos"]) >= 1

    created = client.post(
        "/v1/projects/from-github",
        headers=headers,
        json={"full_name": "octocat-dev/widget-agents"},
    )
    assert created.status_code == 200
    assert created.json()["slug"] == "widget-agents"
    assert created.json()["ingest_api_key"]

    projects = client.get("/v1/projects", headers=headers).json()
    assert any(p["slug"] == "widget-agents" for p in projects)

    removed = client.delete("/v1/projects/widget-agents", headers=headers)
    assert removed.status_code == 200, removed.text
    assert removed.json()["ok"] is True
    projects_after = client.get("/v1/projects", headers=headers).json()
    assert not any(p["slug"] == "widget-agents" for p in projects_after)

    # System demo tabs cannot be disconnected
    blocked = client.delete("/v1/projects/sales-ivr", headers=headers)
    assert blocked.status_code == 403


def test_non_demo_cannot_use_mock_github(client: TestClient):
    reg = client.post(
        "/v1/auth/email/register",
        json={"email": "builder@example.com", "password": "pass1234", "name": "Builder"},
    )
    assert reg.status_code == 200
    headers = {"Authorization": f"Bearer {reg.json()['session_token']}"}
    gh = client.post("/v1/auth/dev/github", headers=headers, json={})
    assert gh.status_code == 501
    assert "not configured" in gh.json()["detail"].lower()

    start = client.get(
        "/v1/auth/github/start",
        params={"intent": "connect", "session_token": reg.json()["session_token"]},
        follow_redirects=False,
    )
    assert start.status_code == 501


def test_ingest_and_query_scoped(client: TestClient, auth_headers: dict):
    batch = {
        "runs": [
            {
                "run_id": "run-1",
                "project_id": "sales-ivr",
                "external_id": "fix-1",
                "status": "succeeded",
                "channel": "cli",
                "outcome": "quoted",
                "started_at": "2026-08-03T12:00:00Z",
                "ended_at": "2026-08-03T12:00:01Z",
            },
            {
                "run_id": "run-2",
                "project_id": "sales-ivr",
                "external_id": "turn-1",
                "status": "succeeded",
                "channel": "web",
                "outcome": "conversation_turn",
                "started_at": "2026-08-03T12:00:00Z",
                "ended_at": "2026-08-03T12:00:00.500Z",
            },
        ],
        "spans": [
            {
                "span_id": "span-1",
                "run_id": "run-1",
                "project_id": "sales-ivr",
                "agent_name": "QuoteGenerationAgent",
                "status": "ok",
            },
            {
                "span_id": "span-2",
                "run_id": "run-1",
                "project_id": "sales-ivr",
                "agent_name": "LookupAgent",
                "status": "ok",
            },
        ],
        "llm_calls": [
            {
                "call_id": "call-1",
                "span_id": "span-1",
                "run_id": "run-1",
                "project_id": "sales-ivr",
                "agent_name": "QuoteGenerationAgent",
                "model": "gpt-4o-mini",
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
                "latency_ms": 20,
                "cost_usd": 0.0001,
            }
        ],
        "tool_calls": [
            {
                "tool_call_id": "tool-1",
                "span_id": "span-2",
                "run_id": "run-1",
                "project_id": "sales-ivr",
                "agent_name": "LookupAgent",
                "tool_name": "rate_lookup",
                "latency_ms": 12,
                "success": True,
            },
            {
                "tool_call_id": "tool-2",
                "span_id": "span-2",
                "run_id": "run-1",
                "project_id": "sales-ivr",
                "agent_name": "LookupAgent",
                "tool_name": "crm_fetch",
                "latency_ms": 40,
                "success": False,
            },
        ],
        "handoffs": [
            {
                "handoff_id": "hand-1",
                "run_id": "run-1",
                "project_id": "sales-ivr",
                "from_span_id": "span-2",
                "to_span_id": "span-1",
                "reason": "quote_ready",
            }
        ],
    }
    resp = client.post(
        "/v1/ingest",
        json=batch,
        headers={"X-API-Key": "dev-sales-ivr-key"},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    bad = client.post(
        "/v1/ingest",
        json=batch,
        headers={"X-API-Key": "wrong"},
    )
    assert bad.status_code == 401

    sales_runs = client.get(
        "/v1/runs", params={"project_id": "sales-ivr"}, headers=auth_headers
    ).json()
    assert len(sales_runs) == 2
    by_id = {r["run_id"]: r for r in sales_runs}
    assert by_id["run-1"]["total_tokens"] == 150
    assert by_id["run-1"]["duration_ms"] == 1000

    ado_runs = client.get(
        "/v1/runs", params={"project_id": "ado-pipeline"}, headers=auth_headers
    ).json()
    assert ado_runs == []

    detail = client.get("/v1/runs/run-1", headers=auth_headers).json()
    assert detail["spans"][0]["agent_name"] in {"QuoteGenerationAgent", "LookupAgent"}
    assert len(detail["tool_calls"]) == 2
    assert len(detail["handoffs"]) == 1

    stats = client.get(
        "/v1/agents/stats", params={"project_id": "sales-ivr"}, headers=auth_headers
    ).json()
    agents = {a["agent_name"]: a for a in stats["agents"]}
    assert "QuoteGenerationAgent" in agents
    assert agents["LookupAgent"]["tool_calls"] == 2
    assert agents["LookupAgent"]["tool_errors"] == 1
    assert agents["LookupAgent"]["tool_error_rate"] == 0.5
    assert agents["QuoteGenerationAgent"]["prompt_tokens"] == 100
    assert agents["QuoteGenerationAgent"]["completion_tokens"] == 50
    assert agents["QuoteGenerationAgent"]["cost_per_run"] == 0.0001

    eff = client.get(
        "/v1/metrics/efficiency", params={"project_id": "sales-ivr"}, headers=auth_headers
    ).json()
    assert eff["run_count"] == 2
    assert eff["successful_runs"] == 1
    assert eff["success_rate"] == 0.5
    assert eff["prompt_tokens"] == 100
    assert eff["completion_tokens"] == 50
    assert eff["tool_call_count"] == 2
    assert eff["tool_error_count"] == 1
    assert eff["tool_error_rate"] == 0.5
    assert eff["p50_latency_ms"] in {500, 1000}
    assert eff["p95_latency_ms"] in {500, 1000}
    assert "cost_per_run" in eff["leaderboard"][0]
    assert eff["leaderboard"][0]["efficiency"] == eff["leaderboard"][0]["cost_per_run"]


def test_github_login_start_asks_for_account(client: TestClient, monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "gh-client")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "gh-secret")
    clear_settings_cache()
    resp = client.get(
        "/v1/auth/github/start",
        params={"intent": "login", "redirect_to": "/auth/callback"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    location = resp.headers["location"]
    assert location.startswith("https://github.com/login/oauth/authorize")
    assert "prompt=select_account" in location
    assert "client_id=gh-client" in location
    assert resp.headers.get("cache-control", "").startswith("no-store")


def test_dev_oauth_login_requires_confirm(client: TestClient):
    gh = client.get("/v1/auth/dev/github/login", follow_redirects=False)
    assert gh.status_code == 200
    assert "text/html" in gh.headers["content-type"]
    assert "token=" not in (gh.headers.get("location") or "")
    assert "Continue with GitHub" in gh.text

    gh_ok = client.get("/v1/auth/dev/github/login", params={"confirm": "1"}, follow_redirects=False)
    assert gh_ok.status_code == 302
    assert "token=" in gh_ok.headers["location"]
