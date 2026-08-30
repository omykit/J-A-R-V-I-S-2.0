import sys
from pathlib import Path

CLIENT_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = CLIENT_DIR.parent

# desktop_app.py imports api_client (client/) and voice_engine (repo root),
# exactly as it does when launched directly.
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(CLIENT_DIR))
