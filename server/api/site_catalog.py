"""O catálogo público do site — o insumo das páginas por exercício (SPEC-026 §Escopo, T-165).

Ninguém procura "Digital Fit". Procuram *"como fazer agachamento correto"* e *"squat form check
app"*. O texto que responde a essas buscas já existe e já é multilíngue desde a T-146 — nome,
grupo muscular, dica do treinador, instrução de cena e passos do guia, tudo no painel — e hoje
só aparece **depois de a câmera abrir**. Este módulo é o que o tira de lá.

## Por que um snapshot exportado, e não o build lendo o banco

A SPEC-026 §Eventos dizia que o pré-render leria o ORM "no build". Não tem como: o
`docker/web.Dockerfile` builda num `node:22-alpine` sem Django e sem Postgres, e no
`scripts/prod.sh up` a ordem é build → migrate → start, então nem a API está de pé nessa hora.

A saída é um passo de exportação **antes** do build: este módulo monta o retrato, o comando
`manage.py export_site_catalog` o escreve como JSON, e o bundle do site o consome como dado
estático. Três coisas que isso compra e que a leitura direta não daria:

  - o build continua **hermético** — roda no CI e na máquina de quem clonou, sem banco;
  - o dado fica **no diff**: mudar o catálogo aparece como alteração de arquivo, revisável, e é
    possível saber que conteúdo estava no ar em cada deploy;
  - o modo de falha é o certo — banco fora do ar não derruba o build, congela o conteúdo.

O preço, dito de frente: exercício despublicado só some do site no **próximo build**. É a
natureza do pré-render, não desta escolha — a página é um arquivo, e arquivo não consulta banco.

## Quem entra

`config.exercises_for(None, locale=...)` — o mesmo resolvedor do `GET /api/config` e da
admissão, com solicitante **anônimo**. Não é atalho: quem chega da busca é anônimo, e a página
existe para levar essa pessoa a um exercício que ela consegue abrir. Um exercício exclusivo de
assinante viraria uma landing para uma porta trancada, e um `beta` viraria página pública de
algo que o produto ainda não sustenta. Os dois eixos já são decididos lá dentro (`enabled`,
`min_plan`, `maturity`); duplicar a regra aqui seria o `[A/T-051]` recomeçando por outro lado.
"""

from __future__ import annotations

from typing import Any

from api.config import exercises_for
from api.i18n import LOCALES, SOURCE_LOCALE

__all__ = ["VERSAO_DO_CATALOGO", "SlugDuplicado", "catalogo_publico"]

#: Versão da FORMA deste documento. O consumidor (`web/src/site/exercicios.ts`) a confere e
#: recusa o que não entende — um snapshot velho num build novo entregaria páginas pela metade,
#: e página pela metade vai para o índice do mesmo jeito.
VERSAO_DO_CATALOGO = 1


class SlugDuplicado(Exception):
    """Dois exercícios disputando o mesmo endereço num idioma.

    Erro e não aviso: o pré-render escreveria os dois no mesmo arquivo e o segundo apagaria o
    primeiro, sem nada acusar — uma página some do site e continua no `sitemap.xml`.
    """


def catalogo_publico(*, locales: tuple[str, ...] = LOCALES) -> dict[str, Any]:
    """O retrato do catálogo que o site publica, em todos os idiomas.

    Ordem estável (a de `exercises_for`, que é `ordem, slug`) porque a saída vai para um arquivo
    versionado: um dicionário que muda de ordem a cada exportação produziria diff de mentira.
    """
    por_locale = {locale: exercises_for(None, locale=locale) for locale in locales}

    slugs = list(
        por_locale[SOURCE_LOCALE]
        if SOURCE_LOCALE in por_locale
        else next(iter(por_locale.values()))
    )

    enderecos = _enderecos_traduzidos(slugs)
    exercicios = [_exercicio(slug, por_locale, locales, enderecos) for slug in slugs]
    _recusar_enderecos_repetidos(exercicios, locales)

    return {"versao": VERSAO_DO_CATALOGO, "exercicios": exercicios}


def _enderecos_traduzidos(slugs: list[str]) -> dict[tuple[str, str], str]:
    """`(slug, locale) -> url_slug`, só das linhas de tradução que realmente têm endereço.

    Lido aqui e não pelo overlay de `exercises_for` porque o fallback é OUTRO — ver o comentário
    em `config._CAMPOS_TRADUZIVEIS_DO_EXERCICIO`.
    """
    from api.models import ExerciseTranslation

    return {
        (linha["exercise__slug"], linha["locale"]): linha["url_slug"]
        for linha in ExerciseTranslation.objects.filter(exercise__slug__in=slugs)
        .exclude(url_slug="")
        .values("exercise__slug", "locale", "url_slug")
    }


def _endereco(slug: str, base: dict[str, Any], locale: str, traduzidos: dict) -> str:
    """O endereço público de um exercício num idioma, com o fallback escrito por extenso.

    - **idioma de origem**: `Exercise.url_slug`, e vazio cai no slug técnico — é o que faz a
      coluna nascer sem migração de dados e sem página quebrada;
    - **qualquer outro**: `ExerciseTranslation.url_slug`, e vazio cai no **slug técnico**,
      nunca na coluna base. Cair na base poria a palavra portuguesa na URL inglesa
      (`/en/exercises/polichinelo/`), que é o oposto do que a página existe para fazer.

    O que falta fica visível em `manage.py i18n_status`, que passou a contar `url_slug` como
    campo traduzível — o mesmo mecanismo que o projeto já usa para buraco de tradução.
    """
    if locale == SOURCE_LOCALE:
        return (base.get("url_slug") or "").strip() or slug
    return traduzidos.get((slug, locale), "").strip() or slug


def _exercicio(
    slug: str,
    por_locale: dict[str, dict[str, Any]],
    locales: tuple[str, ...],
    enderecos: dict[tuple[str, str], str],
):
    """Um exercício: o que não muda com o idioma, e um bloco por idioma do que muda."""
    base = por_locale[SOURCE_LOCALE][slug] if SOURCE_LOCALE in por_locale else {}

    return {
        # O slug TÉCNICO continua aqui, e é o que o botão da página manda para o app: o endereço
        # público é traduzido, o contrato com a admissão não é.
        "slug": slug,
        "category": base.get("category") or "",
        "demo_img": base.get("demo_img") or "",
        "dot_color": base.get("dot_color") or "",
        "met": base.get("met") or 0,
        "por_idioma": {
            locale: _texto(
                por_locale.get(locale, {}).get(slug) or {},
                slug,
                _endereco(slug, base, locale, enderecos),
            )
            for locale in locales
        },
    }


def _texto(ex: dict[str, Any], slug: str, endereco: str) -> dict[str, Any]:
    """Os campos que mudam com o idioma, já com o fallback de `exercises_for` aplicado.

    O texto cai na coluna base quando não há tradução (doutrina da T-146: nunca em branco, nunca
    em chave crua). O `endereco` chega pronto de `_endereco()`, que tem regra própria.
    """
    return {
        "url_slug": endereco,
        "nome": ex.get("display_name") or slug,
        "grupo_muscular": ex.get("muscle_group") or "",
        "dica": ex.get("default_tip") or "",
        "dica_de_cena": ex.get("scene_tip") or "",
        "passos": [
            passo.get("text") or "" for passo in (ex.get("guide_steps") or []) if passo.get("text")
        ],
    }


def _recusar_enderecos_repetidos(
    exercicios: list[dict[str, Any]], locales: tuple[str, ...]
) -> None:
    for locale in locales:
        vistos: dict[str, str] = {}
        for ex in exercicios:
            endereco = ex["por_idioma"][locale]["url_slug"]
            anterior = vistos.get(endereco)
            if anterior is not None:
                raise SlugDuplicado(
                    f"{anterior!r} e {ex['slug']!r} disputam o endereco "
                    f"{endereco!r} em {locale!r}; ajuste o campo 'slug da URL "
                    f"publica' de um dos dois no painel."
                )
            vistos[endereco] = ex["slug"]
