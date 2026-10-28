from __future__ import annotations

import ast
import json
import os
from pathlib import Path
from typing import Any

import httpx
import typer
import yaml
from rich import print as rprint

app = typer.Typer(help="TelemetryBot CLI — connect repos and scan instrumentation", no_args_is_help=True)

CREDENTIALS_PATH = Path.home() / ".telemetrybot" / "credentials.json"


def _collector() -> str:
    return os.environ.get("TELEMETRY_COLLECTOR_URL", "http://localhost:8100").rstrip("/")


def _load_token() -> str | None:
    env = os.environ.get("TELEMETRY_SESSION")
    if env:
        return env
    if CREDENTIALS_PATH.exists():
        try:
            data = json.loads(CREDENTIALS_PATH.read_text(encoding="utf-8"))
            return data.get("session_token")
        except Exception:
            return None
    return None


def _save_token(token: str, email: str | None = None) -> None:
    CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CREDENTIALS_PATH.write_text(
        json.dumps({"session_token": token, "email": email, "collector": _collector()}, indent=2),
        encoding="utf-8",
    )


def _auth_headers() -> dict[str, str]:
    token = _load_token()
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


@app.command()
def whoami() -> None:
    """Show collector URL, health, and signed-in user."""
    url = _collector()
    rprint(f"[bold]collector[/bold]: {url}")
    try:
        resp = httpx.get(f"{url}/health", timeout=5.0)
        rprint(f"[bold]health[/bold]: {resp.json()}")
    except Exception as exc:
        rprint(f"[red]unreachable[/red]: {exc}")
        raise typer.Exit(1) from exc

    token = _load_token()
    if not token:
        rprint("[yellow]not signed in[/yellow] — run [cyan]telemetry login[/cyan]")
        return
    me = httpx.get(f"{url}/v1/auth/me", headers=_auth_headers(), timeout=10.0)
    if me.status_code == 401:
        rprint("[yellow]session expired[/yellow] — run [cyan]telemetry login[/cyan]")
        return
    me.raise_for_status()
    user = me.json()["user"]
    rprint(f"[bold]user[/bold]: {user['email']} ({user.get('name')})")
    if user.get("github_connected"):
        rprint(f"[bold]github[/bold]: {user.get('github_login')}")


@app.command()
def login(
    email: str = typer.Option(..., prompt=True, help="Account email"),
    password: str = typer.Option(..., prompt=True, hide_input=True, help="Password"),
) -> None:
    """Sign in (stores session in ~/.telemetrybot/credentials.json)."""
    url = _collector()
    resp = httpx.post(
        f"{url}/v1/auth/email/login",
        json={"email": email, "password": password},
        timeout=15.0,
    )
    if resp.status_code >= 400:
        rprint(f"[red]login failed[/red]: {resp.json().get('detail', resp.text)}")
        raise typer.Exit(1)
    data = resp.json()
    _save_token(data["session_token"], email=data["user"]["email"])
    rprint(f"[green]Signed in[/green] as {data['user']['email']}")
    rprint(f"credentials → {CREDENTIALS_PATH}")


@app.command()
def logout() -> None:
    """Clear local CLI session."""
    token = _load_token()
    if token:
        try:
            httpx.post(f"{_collector()}/v1/auth/logout", headers=_auth_headers(), timeout=10.0)
        except Exception:
            pass
    if CREDENTIALS_PATH.exists():
        CREDENTIALS_PATH.unlink()
    rprint("[green]Signed out[/green]")


@app.command("projects")
def list_projects() -> None:
    """List registered monitoring projects (tabs)."""
    url = _collector()
    headers = _auth_headers()
    if not headers:
        rprint("[red]Sign in first:[/red] telemetry login")
        raise typer.Exit(1)
    resp = httpx.get(f"{url}/v1/projects", headers=headers, timeout=10.0)
    if resp.status_code == 401:
        rprint("[red]Session expired[/red] — run telemetry login")
        raise typer.Exit(1)
    resp.raise_for_status()
    for p in resp.json():
        rprint(f"• [cyan]{p['slug']}[/cyan] — {p['name']} (id={p['id']})")


@app.command()
def connect(
    path: Path = typer.Argument(..., help="Local path to a workload repo/folder"),
    name: str | None = typer.Option(None, help="Display name"),
    slug: str | None = typer.Option(None, help="Project slug / tab id"),
) -> None:
    """Register a local folder as a TelemetryBot project tab."""
    headers = _auth_headers()
    if not headers:
        rprint("[red]Sign in first:[/red] telemetry login")
        raise typer.Exit(1)

    path = path.resolve()
    if not path.is_dir():
        rprint(f"[red]Not a directory:[/red] {path}")
        raise typer.Exit(1)

    project_slug = slug or path.name
    display = name or path.name.replace("-", " ").title()
    telemetry_yaml = path / "telemetry.yaml"
    api_key = f"dev-{project_slug}-key"

    if telemetry_yaml.exists():
        raw = yaml.safe_load(telemetry_yaml.read_text(encoding="utf-8")) or {}
        project_slug = raw.get("project_slug") or raw.get("project_id") or project_slug
        api_key = raw.get("api_key") or api_key
    else:
        telemetry_yaml.write_text(
            "\n".join(
                [
                    f"collector_url: {_collector()}",
                    f"project_id: {project_slug}",
                    f"project_slug: {project_slug}",
                    f"api_key: {api_key}",
                    "enabled: true",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        rprint(f"Created {telemetry_yaml}")

    body = {
        "id": project_slug,
        "slug": project_slug,
        "name": display,
        "local_path": str(path),
        "ingest_api_key": api_key,
        "is_system": False,
    }
    url = _collector()
    resp = httpx.post(f"{url}/v1/projects", json=body, headers=headers, timeout=10.0)
    if resp.status_code == 409:
        rprint(f"[yellow]Project already registered:[/yellow] {project_slug}")
    elif resp.status_code == 401:
        rprint("[red]Session expired[/red] — run telemetry login")
        raise typer.Exit(1)
    else:
        resp.raise_for_status()
        data = resp.json()
        rprint(f"[green]Connected[/green] tab [cyan]{data['slug']}[/cyan]")
        if data.get("ingest_api_key"):
            rprint(f"ingest key: {data['ingest_api_key']}")

    scan(path)


@app.command()
def scan(
    path: Path = typer.Argument(..., help="Path to scan for agentelemetry usage"),
    project: str | None = typer.Option(None, help="Project id/slug (default: folder name)"),
) -> None:
    """Scan for @trace_agent / agentelemetry imports and upload coverage."""
    headers = _auth_headers()
    if not headers:
        rprint("[red]Sign in first:[/red] telemetry login")
        raise typer.Exit(1)

    path = path.resolve()
    project_ref = project or path.name
    instrumented: list[str] = []
    missing: list[str] = []
    files_scanned = 0

    for py in path.rglob("*.py"):
        if any(part in {"venv", ".venv", "__pycache__", "node_modules", ".git"} for part in py.parts):
            continue
        files_scanned += 1
        text = py.read_text(encoding="utf-8", errors="ignore")
        rel = str(py.relative_to(path))
        uses_sdk = "agentelemetry" in text or "trace_agent" in text or "TelemetryClient" in text
        looks_like_agent = "Agent" in py.stem or "/agents/" in rel.replace("\\", "/")
        if uses_sdk:
            instrumented.append(rel)
        elif looks_like_agent:
            try:
                tree = ast.parse(text)
                has_fn = any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in tree.body)
            except SyntaxError:
                has_fn = True
            if has_fn:
                missing.append(rel)

    bridge = path / "sales_ivr" / "telemetry.py"
    if bridge.exists() and str(bridge.relative_to(path)) not in instrumented:
        instrumented.append(str(bridge.relative_to(path)))

    report = {
        "files_scanned": files_scanned,
        "instrumented": sorted(set(instrumented)),
        "missing": sorted(set(missing)),
        "notes": "Heuristic scan for agentelemetry imports and agent-like modules",
    }
    rprint(f"Scanned {files_scanned} files — instrumented={len(report['instrumented'])} missing={len(report['missing'])}")
    for item in report["instrumented"][:20]:
        rprint(f"  [green]OK[/green] {item}")
    for item in report["missing"][:20]:
        rprint(f"  [yellow]??[/yellow] {item}")

    url = _collector()
    resp = httpx.post(
        f"{url}/v1/projects/{project_ref}/coverage",
        json=report,
        headers=headers,
        timeout=10.0,
    )
    if resp.status_code == 404:
        rprint(f"[red]Project not found:[/red] {project_ref} — run telemetry connect first")
        raise typer.Exit(1)
    if resp.status_code == 401:
        rprint("[red]Session expired[/red] — run telemetry login")
        raise typer.Exit(1)
    resp.raise_for_status()
    rprint(f"[green]Coverage uploaded[/green] for {project_ref}")


if __name__ == "__main__":
    app()
