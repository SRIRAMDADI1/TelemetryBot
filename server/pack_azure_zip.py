"""Build a Linux-safe zip for Azure App Service zip-deploy (collector).

Do NOT use PowerShell Compress-Archive for this. It stores entries with
backslashes (app\\main.py). Linux unzip/Oryx then fails to create a real
app/ package directory → ModuleNotFoundError: No module named 'app'.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / "telemetrybot-collector-deploy.zip"

INCLUDE_FILES = [
    "asgi.py",
    "startup.sh",
    "requirements.txt",
    "pyproject.toml",
    "README.md",
]
INCLUDE_DIRS = [
    "app",
]

SKIP_DIR_NAMES = {
    "__pycache__",
    ".venv",
    "venv",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".git",
    "tests",
}
SKIP_SUFFIXES = {".pyc", ".pyo", ".db"}


def should_skip(path: Path) -> bool:
    if path.name in SKIP_DIR_NAMES:
        return True
    if path.suffix in SKIP_SUFFIXES:
        return True
    if path.name.startswith(".env"):
        return True
    return False


def add_file(zf: zipfile.ZipFile, path: Path) -> None:
    arcname = path.relative_to(ROOT).as_posix()  # forward slashes for Linux
    if path.name.endswith(".sh"):
        data = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        zf.writestr(arcname, data)
        return
    zf.write(path, arcname)


def main() -> None:
    missing = [name for name in INCLUDE_FILES if not (ROOT / name).is_file()]
    missing += [name for name in INCLUDE_DIRS if not (ROOT / name).is_dir()]
    if missing:
        raise SystemExit(f"Missing required paths: {missing}")

    if OUT.exists():
        OUT.unlink()

    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in INCLUDE_FILES:
            add_file(zf, ROOT / name)
        for dirname in INCLUDE_DIRS:
            base = ROOT / dirname
            for path in base.rglob("*"):
                if path.is_dir():
                    continue
                if any(part in SKIP_DIR_NAMES for part in path.parts):
                    continue
                if should_skip(path):
                    continue
                add_file(zf, path)

    with zipfile.ZipFile(OUT, "r") as zf:
        names = zf.namelist()
    if "app/main.py" not in names:
        raise SystemExit(
            "Zip is invalid: missing app/main.py (forward-slash entry). "
            f"Sample entries: {names[:10]}"
        )
    if "asgi.py" not in names or "startup.sh" not in names:
        raise SystemExit("Zip is invalid: missing asgi.py or startup.sh")

    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes, {len(names)} entries)")
    print("OK: app/main.py present with forward slashes")


if __name__ == "__main__":
    main()
