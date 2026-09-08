"""Main application entry point for the Privacy-Preserving Vision Browser Agent backend.

Exposes 'app' for uvicorn:
  Inside server/: python -m uvicorn main:app --reload
  From root:      python -m uvicorn server.main:app --reload
"""
import sys
from pathlib import Path

# Ensure both server/ and workspace root are in sys.path
SERVER_DIR = Path(__file__).resolve().parent
ROOT_DIR = SERVER_DIR.parent
for p in (str(ROOT_DIR), str(SERVER_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from server.api import app
except ModuleNotFoundError:
    from api import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
