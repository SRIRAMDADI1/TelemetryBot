"""Build a Linux-safe zip for Azure App Service zip-deploy (dashboard).

Do NOT use PowerShell Compress-Archive. It stores backslash paths that Linux
unzip/Oryx often mishandles.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / "telemetrybot-dashboard-deploy.zip"

INCLUDE_FILES = [
    "package.json",
    "package-lock.json",
    "next.config.js",
    "tsconfig.json",
    "tailwind.config.js",
    "postcss.config.js",
    "next-env.d.ts",
    "middleware.ts",
    "startup.sh",
]
INCLUDE_DIRS = [
    "app",
    "components",
    "lib",
    "public",
]

SKIP_DIR_NAMES = {
    "node_modules",
    ".next",
    ".git",
}
SKIP_SUFFIXES = {".map"}


def should_skip(path: Path) -> bool:
    if path.name in SKIP_DIR_NAMES:
        return True
    if path.suffix in SKIP_SUFFIXES:
        return True
    if path.name.startswith(".env"):
        return True
    if path.name.endswith(".tsbuildinfo"):
        return True
    return False


def add_file(zf: zipfile.ZipFile, path: Path) -> None:
    arcname = path.relative_to(ROOT).as_posix()
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
    required = ["package.json", "startup.sh", "app/layout.tsx", "public/sitemap.xml"]
    for item in required:
        if item not in names:
            raise SystemExit(f"Zip is invalid: missing {item}. Sample: {names[:12]}")

    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes, {len(names)} entries)")
    print("OK: dashboard zip uses forward-slash paths")


if __name__ == "__main__":
    main()
