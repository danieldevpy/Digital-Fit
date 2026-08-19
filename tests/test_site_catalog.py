"""O catálogo público do site — o insumo das páginas por exercício (SPEC-026, T-165).

Três coisas para provar:

1. O retrato sai do MESMO resolvedor que o `GET /api/config` e a admissão usam
   (`exercises_for`), com solicitante anônimo — então "some do catálogo" e "some do site" são o
   mesmo evento, e não duas regras que podem divergir.
2. O endereço público é **traduzido** e cai com honestidade: `url_slug` vazio usa o slug
   técnico, nunca deixa a página sem URL.
3. O comando falha alto onde falhar calado custaria caro: dois exercícios no mesmo endereço, e
   arquivo versionado fora de dia com o banco.
"""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

import pytest
from api.config import SNAPSHOT_KEY
from api.models import Exercise, ExerciseTranslation
from api.site_catalog import VERSAO_DO_CATALOGO, SlugDuplicado, catalogo_publico
from django.core.cache import cache
from django.core.management import CommandError, call_command

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _limpa_snapshot():
    cache.delete(SNAPSHOT_KEY)
    yield
    cache.delete(SNAPSHOT_KEY)


def _do_slug(catalogo: dict, slug: str) -> dict:
    for ex in catalogo["exercicios"]:
        if ex["slug"] == slug:
            return ex
    raise AssertionError(
        f"{slug} nao esta no catalogo publico: {[e['slug'] for e in catalogo['exercicios']]}"
    )


# ------------------------------------------------------------------------------------------
# Quem entra
# ------------------------------------------------------------------------------------------


def test_traz_os_exercicios_que_um_anonimo_consegue_abrir() -> None:
    catalogo = catalogo_publico()

    assert catalogo["versao"] == VERSAO_DO_CATALOGO
    assert catalogo["exercicios"], "o catalogo publico nasceu vazio"
    assert _do_slug(catalogo, "squat")


def test_exercicio_desligado_no_painel_sai_do_site() -> None:
    """A mesma edição que o tira do app tira a página — é o critério da task, e é um `enabled`.

    Sem isto haveria duas regras de publicação (uma do app, outra do site) e elas divergiriam:
    a página continuaria no `sitemap.xml`, o robô entraria, e o botão levaria a um exercício que
    a admissão recusa.
    """
    Exercise.objects.filter(slug="squat").update(enabled=False)
    cache.delete(SNAPSHOT_KEY)

    slugs = [ex["slug"] for ex in catalogo_publico()["exercicios"]]

    assert "squat" not in slugs


# ------------------------------------------------------------------------------------------
# O endereço, que é o motivo da task
# ------------------------------------------------------------------------------------------


def test_url_slug_vazio_cai_no_slug_tecnico() -> None:
    """Nasce sem migração de dado: coluna em branco não pode produzir página sem endereço."""
    Exercise.objects.filter(slug="squat").update(url_slug="")
    cache.delete(SNAPSHOT_KEY)

    squat = _do_slug(catalogo_publico(), "squat")

    assert squat["por_idioma"]["pt-BR"]["url_slug"] == "squat"
    assert squat["por_idioma"]["en"]["url_slug"] == "squat"


def test_o_endereco_e_traduzido_por_idioma() -> None:
    """`/exercicios/agachamento/` e `/en/exercises/squat/` — a palavra na URL é sinal de busca.

    É a razão declarada da task: ninguém procura "Digital Fit", procuram "agachamento" e "squat".
    Traduzir só o texto e deixar o endereço em inglês entregaria metade do ganho.
    """
    Exercise.objects.filter(slug="squat").update(url_slug="agachamento")
    ExerciseTranslation.objects.update_or_create(
        exercise=Exercise.objects.get(slug="squat"),
        locale="en",
        defaults={"url_slug": "squat", "display_name": "Squat"},
    )
    cache.delete(SNAPSHOT_KEY)

    squat = _do_slug(catalogo_publico(), "squat")

    assert squat["por_idioma"]["pt-BR"]["url_slug"] == "agachamento"
    assert squat["por_idioma"]["en"]["url_slug"] == "squat"
    # O slug TÉCNICO não se move: é o que o botão da página manda para a admissão.
    assert squat["slug"] == "squat"


def test_texto_sem_traducao_cai_na_coluna_base_e_nunca_em_branco() -> None:
    """Mesma doutrina da T-146: falta de tradução mostra o português, nunca vazio nem chave crua."""
    Exercise.objects.filter(slug="squat").update(display_name="Agachamento")
    ExerciseTranslation.objects.filter(exercise__slug="squat", locale="en").delete()
    cache.delete(SNAPSHOT_KEY)

    squat = _do_slug(catalogo_publico(), "squat")

    assert squat["por_idioma"]["en"]["nome"] == "Agachamento"


def test_dois_exercicios_no_mesmo_endereco_param_a_exportacao() -> None:
    """Falhar alto: o pré-render escreveria os dois no mesmo arquivo, e o segundo apaga o primeiro.

    O sintoma seria uma página sumindo do site e continuando no `sitemap.xml` — robô convidado a
    entrar numa URL que não existe, sem nada acusar.
    """
    dois = list(Exercise.objects.filter(enabled=True)[:2])
    if len(dois) < 2:
        pytest.skip("o catalogo semeado tem menos de dois exercicios habilitados")
    for ex in dois:
        Exercise.objects.filter(pk=ex.pk).update(url_slug="agachamento")
    cache.delete(SNAPSHOT_KEY)

    with pytest.raises(SlugDuplicado, match="agachamento"):
        catalogo_publico()


# ------------------------------------------------------------------------------------------
# O comando
# ------------------------------------------------------------------------------------------


def test_comando_escreve_json_legivel(tmp_path: Path) -> None:
    destino = tmp_path / "exercicios.json"

    call_command("export_site_catalog", "--out", str(destino))

    texto = destino.read_text(encoding="utf-8")
    assert texto.endswith("\n"), "arquivo versionado precisa terminar em quebra de linha"
    dados = json.loads(texto)
    assert dados["versao"] == VERSAO_DO_CATALOGO
    assert dados["exercicios"]


def test_check_acusa_arquivo_desatualizado(tmp_path: Path) -> None:
    """O portão do CI: exercício novo sem reexportar não pode passar em silêncio.

    É o mesmo papel que o `i18n_status` tem para tradução — um buraco que só apareceria meses
    depois, como "por que este exercício não tem página?".
    """
    destino = tmp_path / "exercicios.json"
    call_command("export_site_catalog", "--out", str(destino))

    call_command("export_site_catalog", "--out", str(destino), "--check", stdout=StringIO())

    Exercise.objects.filter(slug="squat").update(url_slug="agachamento-novo")
    cache.delete(SNAPSHOT_KEY)

    with pytest.raises(CommandError, match="desatualizado"):
        call_command("export_site_catalog", "--out", str(destino), "--check")


def test_o_arquivo_versionado_esta_em_dia_com_as_migrations() -> None:
    """O portão do repositório: exercício novo sem reexportar não passa nos gates.

    Roda contra o banco de teste, que é semeado pelas MESMAS migrations que rodam em produção —
    então "o que uma instalação nova teria" e "o que está versionado" precisam ser a mesma coisa.
    Sem este caso, acrescentar um exercício por migration deixaria o site sem a página dele até
    alguém reparar, e reparar levaria meses: nada quebra, a página simplesmente não existe.

    Não confere o banco de PRODUÇÃO, que tem edições de painel em cima — quem cuida daquele lado
    é o `exporta_catalogo_do_site` do `scripts/prod.sh`, que reexporta a cada deploy.
    """
    versionado = Path(__file__).resolve().parents[1] / "web" / "src" / "site" / "exercicios.json"

    assert versionado.exists(), f"{versionado} nao existe — rode `manage.py export_site_catalog`"
    call_command("export_site_catalog", "--out", str(versionado), "--check", stdout=StringIO())


def test_saida_e_estavel_entre_duas_exportacoes(tmp_path: Path) -> None:
    """Diff de mentira é pior que diff nenhum: o arquivo é versionado e revisado por gente."""
    um, outro = tmp_path / "a.json", tmp_path / "b.json"

    call_command("export_site_catalog", "--out", str(um))
    cache.delete(SNAPSHOT_KEY)
    call_command("export_site_catalog", "--out", str(outro))

    assert um.read_text(encoding="utf-8") == outro.read_text(encoding="utf-8")
