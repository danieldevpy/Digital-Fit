"""Smoke tests do esqueleto do monorepo (T-001).

Garantem que os dois lados importam de forma independente: o Django sobe e os
workers sao importaveis sem Django no path.
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_repo_layout() -> None:
    for relative in (
        "docker-compose.yml",
        "pyproject.toml",
        "docker/server.Dockerfile",
        "server/manage.py",
        "server/core/settings.py",
        "workers/shared/__init__.py",
        "web/README.md",
    ):
        assert (REPO_ROOT / relative).exists(), f"faltando: {relative}"


def test_healthz_responde_ok(client) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_settings_leem_ambiente() -> None:
    from django.conf import settings

    assert settings.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql"
    assert settings.REDIS_URL.startswith("redis://")


def test_workers_nao_importam_django() -> None:
    """`workers.shared` deve importar em um processo sem DJANGO_SETTINGS_MODULE."""
    programa = "import sys; import workers.shared; assert 'django' not in sys.modules"
    result = subprocess.run(
        [sys.executable, "-c", programa],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
