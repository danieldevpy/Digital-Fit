"""Buraco de tradução no banco — visível, nunca silencioso (SPEC-025 §Tabela de tradução, T-146).

`config.exercises_for`/`config_payload` cumprem a metade "nunca em branco, nunca em chave
crua" do critério 4 sozinhos: falta tradução, cai na coluna base (pt-BR), e quem treina em
inglês nunca vê um buraco na tela. Mas fallback honesto tem um efeito colateral — ele esconde a
dívida. Um exercício cadastrado no painel sem tradução funciona perfeitamente bem em produção,
em português, para todo visitante inglês, e ninguém percebe até reparar de olho na tela errada.

Este módulo é a outra metade do critério: "sai listado no `i18n_status`". Mesma doutrina do
`api/exercise_health.py` (T-104) — um número medido substitui uma opinião — só que aqui o que se
mede não é comportamento em produção, é lacuna de conteúdo, e por isso a leitura é direta no
banco, sem janela de tempo.

## Por que um campo só conta como buraco quando a fonte tem o que traduzir

`Exercise.muscle_group` e `Plan.quota_message` são `blank=True` de propósito — nem todo
exercício tem grupo muscular anotado, nem todo plano tem mensagem de recusa (o assinante não
tem quota). Reportar "falta traduzir" para um campo que está vazio na própria fonte pt-BR seria
ruído: não há texto nenhum para traduzir, então não há buraco. O gap só existe quando a coluna
base tem conteúdo real e a tradução não o acompanha.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from api.i18n import LOCALES, SOURCE_LOCALE

__all__ = [
    "CAMPOS_EXERCICIO",
    "CAMPOS_PLANO",
    "LOCALES_TRADUZIVEIS",
    "ExerciseGap",
    "PlanGap",
    "Relatorio",
    "coletar",
]

#: Os idiomas que precisam de linha de tradução — todo `LOCALES` exceto a fonte. Hoje só `en`;
#: um terceiro locale entra aqui de graça, a mesma promessa de
#: `models.TRANSLATABLE_LOCALE_CHOICES`.
LOCALES_TRADUZIVEIS: tuple[str, ...] = tuple(
    locale for locale in LOCALES if locale != SOURCE_LOCALE
)

#: Espelha `config._CAMPOS_TRADUZIVEIS_DO_EXERCICIO` e os campos de `ExerciseTranslation`.
CAMPOS_EXERCICIO: tuple[str, ...] = (
    "display_name",
    "muscle_group",
    "default_tip",
    "scene_tip",
    "url_slug",
)

#: Espelha os campos de `PlanTranslation`.
CAMPOS_PLANO: tuple[str, ...] = ("nome", "quota_message")


@dataclass(frozen=True, slots=True)
class ExerciseGap:
    """Um exercício que tem texto em pt-BR sem contrapartida em `locale`."""

    slug: str
    display_name: str
    locale: str
    #: Campos de `Exercise` com conteúdo na fonte e sem tradução (ou tradução em branco).
    campos_faltando: tuple[str, ...] = ()
    #: Passos do guia (SPEC-015) sem `ExerciseGuideStepTranslation.texto` para este locale.
    passos_faltando: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "exercise": self.slug,
            "display_name": self.display_name,
            "locale": self.locale,
            "campos_faltando": list(self.campos_faltando),
            "passos_faltando": self.passos_faltando,
        }


@dataclass(frozen=True, slots=True)
class PlanGap:
    """Um plano que tem texto em pt-BR sem contrapartida em `locale`."""

    slug: str
    nome: str
    locale: str
    campos_faltando: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan": self.slug,
            "nome": self.nome,
            "locale": self.locale,
            "campos_faltando": list(self.campos_faltando),
        }


@dataclass(frozen=True, slots=True)
class Relatorio:
    """O que falta traduzir agora, nas três tabelas da SPEC-025 §Tabela de tradução."""

    exercicios: list[ExerciseGap] = field(default_factory=list)
    planos: list[PlanGap] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.exercicios) + len(self.planos)

    @property
    def ok(self) -> bool:
        """`True` quando não há buraco nenhum — o estado que o release quer ver."""
        return self.total == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "total": self.total,
            "exercicios": [gap.to_dict() for gap in self.exercicios],
            "planos": [gap.to_dict() for gap in self.planos],
        }


def _campos_faltando(fonte: Any, traducao: Any | None, campos: tuple[str, ...]) -> tuple[str, ...]:
    """Campos de `campos` com conteúdo em `fonte` e sem contrapartida não vazia em `traducao`.

    `traducao` pode ser `None` (nenhuma linha para este locale) — nesse caso todo campo com
    conteúdo na fonte é um buraco, exatamente como se a linha existisse toda em branco.
    """
    faltando = []
    for campo in campos:
        se_a_fonte_tem_texto = bool(getattr(fonte, campo))
        se_a_traducao_tem_texto = bool(traducao and getattr(traducao, campo))
        if se_a_fonte_tem_texto and not se_a_traducao_tem_texto:
            faltando.append(campo)
    return tuple(faltando)


def coletar(*, apenas_habilitados: bool = True) -> Relatorio:
    """Varre `Exercise`/`ExerciseGuideStep`/`Plan` e devolve o que falta traduzir, por locale.

    `apenas_habilitados=True` (padrão) é o mesmo recorte do catálogo servido
    (`config.exercises_for`): um exercício desligado não chega a cliente nenhum, então uma
    tradução que falta nele não é dívida de release — é um exercício fora do ar, outro
    problema, de outro comando (`exercise_health`). `--todos` na linha de comando destrava o
    inventário completo, para quem está justamente preparando o exercício para ligar.
    """
    from api.models import Exercise, Plan

    gaps_exercicio: list[ExerciseGap] = []
    exercicios = Exercise.objects.all()
    if apenas_habilitados:
        exercicios = exercicios.filter(enabled=True)
    exercicios = exercicios.prefetch_related(
        "translations", "guide_steps", "guide_steps__translations"
    ).order_by("ordem", "slug")

    for exercicio in exercicios:
        traducoes = {t.locale: t for t in exercicio.translations.all()}
        passos = list(exercicio.guide_steps.all())
        for locale in LOCALES_TRADUZIVEIS:
            traducao = traducoes.get(locale)
            campos_faltando = _campos_faltando(exercicio, traducao, CAMPOS_EXERCICIO)
            passos_faltando = sum(
                1
                for passo in passos
                if not any(t.locale == locale and t.texto for t in passo.translations.all())
            )
            if campos_faltando or passos_faltando:
                gaps_exercicio.append(
                    ExerciseGap(
                        slug=exercicio.slug,
                        display_name=exercicio.display_name,
                        locale=locale,
                        campos_faltando=campos_faltando,
                        passos_faltando=passos_faltando,
                    )
                )

    gaps_plano: list[PlanGap] = []
    planos = Plan.objects.all().prefetch_related("translations").order_by("ordem", "slug")
    for plano in planos:
        traducoes = {t.locale: t for t in plano.translations.all()}
        for locale in LOCALES_TRADUZIVEIS:
            campos_faltando = _campos_faltando(plano, traducoes.get(locale), CAMPOS_PLANO)
            if campos_faltando:
                gaps_plano.append(
                    PlanGap(
                        slug=plano.slug,
                        nome=plano.nome,
                        locale=locale,
                        campos_faltando=campos_faltando,
                    )
                )

    return Relatorio(exercicios=gaps_exercicio, planos=gaps_plano)
