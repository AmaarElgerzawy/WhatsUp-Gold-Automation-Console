from pathlib import Path
from dotenv import load_dotenv

# Load .env: repo root first, then WebUI/Backend (overrides) so WUG_* is found reliably
_backend_dir = Path(__file__).resolve().parent
_repo_root = _backend_dir.parent.parent
load_dotenv(_repo_root / ".env")
load_dotenv(_backend_dir / ".env", override=True)

from wug_backend.app_factory import create_app

# FastAPI ASGI app (imported by uvicorn)
app = create_app()
