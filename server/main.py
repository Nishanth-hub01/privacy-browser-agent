"""Main application entry point for the Privacy-Preserving Vision Browser Agent backend.

Exposes 'app' for uvicorn:
  Inside server/: python -m uvicorn main:app --reload
  From root:      python -m uvicorn server.main:app --reload
"""
import sys
from pathlib import Path

# Load .env file (GEMINI_API_KEY, LLM_PROVIDER, GEMINI_MODEL, etc.) before anything else
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    # The repo .env is the explicit project configuration; it should override stale
    # shell variables so a user-configured Gemini provider is not silently replaced by
    # an old Ollama environment value.
    load_dotenv(dotenv_path=_env_path, override=True)
except ImportError:
    pass  # python-dotenv not installed; rely on shell environment

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
    app_target = "server.main:app" if Path.cwd() == ROOT_DIR else "main:app"
    uvicorn.run(app_target, host="0.0.0.0", port=8000, reload=True)
