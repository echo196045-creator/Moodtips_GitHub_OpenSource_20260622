from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn


PROJECT_ROOT = Path(__file__).resolve().parent
APP_DIR = PROJECT_ROOT / "04_code" / "05_product_demo"

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from moodsips_fastapi_service_20260404 import app  # noqa: E402


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)
