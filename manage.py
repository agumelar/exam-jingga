#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def load_env(base_dir):
    """Baca .env sebelum settings dipilih, supaya DJANGO_SETTINGS_MODULE di server ikut terpakai."""
    load_dotenv(Path(base_dir) / '.env')


def main():
    """Run administrative tasks."""
    base_dir = Path(__file__).resolve().parent
    load_env(base_dir)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

    # Add apps directory to sys.path
    apps_dir = str(base_dir / 'apps')
    if apps_dir not in sys.path:
        sys.path.insert(0, apps_dir)

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
