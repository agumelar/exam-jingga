"""manage.py membaca .env sebelum memilih settings, supaya shell di server memakai database produksi."""
import os

import manage


def test_settings_module_from_env_file(tmp_path, monkeypatch):
    monkeypatch.delenv('DJANGO_SETTINGS_MODULE', raising=False)
    (tmp_path / '.env').write_text('DJANGO_SETTINGS_MODULE=config.settings.production\n', encoding='utf-8')

    manage.load_env(tmp_path)

    assert os.environ['DJANGO_SETTINGS_MODULE'] == 'config.settings.production'


def test_existing_environment_wins_over_env_file(tmp_path, monkeypatch):
    monkeypatch.setenv('DJANGO_SETTINGS_MODULE', 'config.settings.development')
    (tmp_path / '.env').write_text('DJANGO_SETTINGS_MODULE=config.settings.production\n', encoding='utf-8')

    manage.load_env(tmp_path)

    assert os.environ['DJANGO_SETTINGS_MODULE'] == 'config.settings.development'


def test_missing_env_file_is_ignored(tmp_path, monkeypatch):
    monkeypatch.delenv('DJANGO_SETTINGS_MODULE', raising=False)

    manage.load_env(tmp_path)

    assert 'DJANGO_SETTINGS_MODULE' not in os.environ
