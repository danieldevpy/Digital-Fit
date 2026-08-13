"""Smoke tests do esqueleto do monorepo (T-001).

Garantem que os dois lados importam de forma independente: o Django sobe e os
workers sao importaveis sem Django no path.
"""

import json
import os
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


def _settings_num_processo_limpo(**ambiente: str) -> dict[str, str]:
    """Importa `core.settings` num processo próprio, com o ambiente pedido.

    Em processo, este teste não teria como perguntar nada: a suíte roda sob
    `core.settings_test` (T-076), que já fixou SQLite antes do Django ler qualquer coisa, e
    `django.conf.settings` guarda uma cópia feita no `setup()`. O subprocesso é o mesmo
    recurso que o `test_workers_nao_importam_django` logo abaixo usa, e pelo mesmo motivo:
    a pergunta é sobre o que acontece na IMPORTAÇÃO, então precisa de uma importação nova.
    """
    programa = (
        "import json, core.settings as s; "
        "print(json.dumps({'engine': s.DATABASES['default']['ENGINE'], 'redis': s.REDIS_URL}))"
    )
    env = {key: value for key, value in os.environ.items() if key not in _VARIAVEIS_DA_SUITE}
    env["PYTHONPATH"] = os.pathsep.join([str(REPO_ROOT), str(REPO_ROOT / "server")])
    env.update(ambiente)

    resultado = subprocess.run(
        [sys.executable, "-c", programa],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert resultado.returncode == 0, resultado.stderr
    return json.loads(resultado.stdout)


#: O que `core/settings_test.py` põe no ambiente deste processo. Precisa sair do subprocesso,
#: senão o teste do caminho de produção herdaria o SQLite da suíte e passaria por engano.
_VARIAVEIS_DA_SUITE = ("DJANGO_DB_SQLITE", "DJANGO_CACHE_LOCMEM", "DJANGO_DB_SQLITE_PATH")


def test_settings_leem_ambiente() -> None:
    """O settings decide banco e Redis pelo AMBIENTE — a regra, não o valor de hoje.

    A versão anterior afirmava `ENGINE == postgresql` lendo o settings da própria suíte, que
    roda em SQLite: o teste e a configuração de teste não podiam estar certos ao mesmo tempo
    (Descoberta `[A/T-072]`). O que interessa é que as duas pontas da variável funcionem.
    """
    producao = _settings_num_processo_limpo(REDIS_URL="redis://exemplo:6379/7")
    assert producao["engine"] == "django.db.backends.postgresql"
    assert producao["redis"] == "redis://exemplo:6379/7"

    teste = _settings_num_processo_limpo(DJANGO_DB_SQLITE="1")
    assert teste["engine"] == "django.db.backends.sqlite3"
    assert teste["redis"].startswith("redis://")


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
