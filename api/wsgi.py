import os
import sys
import traceback
from pathlib import Path

# Ensure the project's 'web' folder is on sys.path so `maganghub` package can be imported
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
WEB_PATH = ROOT / 'web'
if str(WEB_PATH) not in sys.path:
    sys.path.insert(0, str(WEB_PATH))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maganghub.settings')

# Import and expose the WSGI application; print traceback on failure so Vercel logs show it
try:
    from maganghub.wsgi import application
    # Vercel's python runtime expects a variable named `app` for WSGI/ASGI compatibility
    app = application
except Exception:
    traceback.print_exc(file=sys.stderr)
    raise
