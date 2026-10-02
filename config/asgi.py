"""ASGI config for Exam Jingga DATH Stack project."""
import os
import sys
from pathlib import Path
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

base_dir = Path(__file__).resolve().parent.parent
apps_dir = str(base_dir / 'apps')
if apps_dir not in sys.path:
    sys.path.insert(0, apps_dir)

application = get_asgi_application()
