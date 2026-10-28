"""Azure App Service ASGI entry (zip root).

Oryx may run gunicorn with cwd under /tmp/<extract> or wwwroot.
Putting `asgi.py` next to the `app/` package keeps the import path stable.

Do not name this file `app.py` — that would shadow the `app` package.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.main import app  # noqa: E402

__all__ = ["app"]
