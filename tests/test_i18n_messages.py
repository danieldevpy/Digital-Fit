"""Texto do servidor em arquivo — conquistas e `detail` de erro (SPEC-025, T-145).

Paridade de chaves entre `messages.pt-BR.yaml` e `messages.en.yaml` é o critério de aceite 5 da
spec vestido de teste: um `git commit` que acrescenta uma frase em português e esquece o inglês
tem de quebrar aqui, sem ninguém precisar lembrar de conferir.
"""

from __future__ import annotations

import pytest
from api import engagement as eng
from api.i18n import LOCALES, SOURCE_LOCALE
from api.i18n.messages import MESSAGES_DIR, Messages, load

# ==========================================================================================
# Os dois arquivos existem e carregam
# ==========================================================================================


def test_messages_dir_tem_um_arquivo_por_locale_suportado() -> None:
    for locale in LOCALES:
        assert (MESSAGES_DIR / f"messages.{locale}.yaml").exists()


def test_load_devolve_messages() -> None:
    assert isinstance(load(SOURCE_LOCALE), Messages)


def test_load_sem_argumento_e_a_fonte() -> None:
    """`lru_cache` guarda `load()` e `load("pt-BR")` em entradas distintas (assinaturas
    diferentes) — o que importa é o CONTEÚDO ser o mesmo, não a identidade do objeto."""
    assert load() == load(SOURCE_LOCALE)


def test_idioma_sem_arquivo_cai_no_source_locale() -> None:
    """Locale sem `messages.<locale>.yaml` próprio nunca estoura — mesmo comportamento do
    `FeedbackCatalog` (T-144), pelo mesmo motivo: locale é preferência de exibição."""
    catalogo = load("fr")

    assert catalogo.achievements == load(SOURCE_LOCALE).achievements
    assert catalogo.errors == load(SOURCE_LOCALE).errors


# ==========================================================================================
# Paridade de chaves entre pt-BR e en — critério de aceite 5 da spec
# ==========================================================================================


def test_paridade_de_chaves_de_conquista_entre_pt_br_e_en() -> None:
    pt = load("pt-BR")
    en = load("en")

    assert pt.achievements.keys() == en.achievements.keys(), (
        "messages.pt-BR.yaml e messages.en.yaml precisam das MESMAS conquistas"
    )


def test_paridade_de_chaves_de_erro_entre_pt_br_e_en() -> None:
    pt = load("pt-BR")
    en = load("en")

    assert pt.errors.keys() == en.errors.keys(), (
        "messages.pt-BR.yaml e messages.en.yaml precisam das MESMAS chaves de erro"
    )


def test_cada_entrada_de_conquista_tem_name_e_description_nos_dois_idiomas() -> None:
    for locale in ("pt-BR", "en"):
        catalogo = load(locale)
        for slug, entrada in catalogo.achievements.items():
            assert entrada.get("name"), f"{locale}: {slug} sem name"
            assert entrada.get("description"), f"{locale}: {slug} sem description"


# ==========================================================================================
# Cobertura total do catálogo de conquistas (ACHIEVEMENTS) — nenhum slug esquecido no YAML
# ==========================================================================================


def test_todo_slug_de_achievements_tem_entrada_nos_dois_idiomas() -> None:
    """`ACHIEVEMENTS` (`api/engagement.py`) só tem slug + predicado desde a T-145; o texto tem
    de existir no catálogo, ou a galeria mostraria uma conquista muda."""
    slugs = {c.slug for c in eng.ACHIEVEMENTS}

    for locale in ("pt-BR", "en"):
        catalogo = load(locale)
        faltando = slugs - catalogo.achievements.keys()
        assert not faltando, f"messages.{locale}.yaml não cobre: {faltando}"


# ==========================================================================================
# `Messages.achievement` — fallback por chave para SOURCE_LOCALE
# ==========================================================================================


def test_achievement_resolve_pelo_slug() -> None:
    entrada = load("pt-BR").achievement("primeira-sessao")

    assert entrada["name"] == "Primeira sessão"
    assert "primeira vez" in entrada["description"]


def test_achievement_em_ingles_e_diferente_do_pt_br() -> None:
    pt = load("pt-BR").achievement("milheiro")
    en = load("en").achievement("milheiro")

    assert pt["name"] != en["name"]
    assert pt["description"] != en["description"]


def test_achievement_slug_desconhecido_devolve_vazio() -> None:
    assert load("pt-BR").achievement("nao-existe") == {}


# ==========================================================================================
# `Messages.error` — interpolação e fallback
# ==========================================================================================


def test_error_devolve_o_texto_do_locale() -> None:
    assert load("pt-BR").error("auth_required") == "autenticacao necessaria"
    assert load("en").error("auth_required") == "authentication required"


def test_error_interpola_por_str_format() -> None:
    texto = load("pt-BR").error("counted_unavailable", ceiling_s=30)

    assert "30 s" in texto
    assert "modo contado" in texto


def test_error_chave_desconhecida_devolve_a_propria_chave() -> None:
    """Nunca `KeyError`: locale é preferência de exibição, não parâmetro que recusa nada."""
    assert load("pt-BR").error("chave-que-nao-existe") == "chave-que-nao-existe"


@pytest.mark.parametrize(
    "chave",
    [
        "email_required",
        "email_invalid",
        "password_required",
        "email_taken",
        "invalid_credentials",
        "refresh_required",
        "refresh_invalid",
        "auth_required",
        "counted_unavailable",
    ],
)
def test_toda_chave_de_erro_usada_no_codigo_existe_nos_dois_idiomas(chave: str) -> None:
    for locale in ("pt-BR", "en"):
        assert chave in load(locale).errors, f"messages.{locale}.yaml sem a chave {chave!r}"
