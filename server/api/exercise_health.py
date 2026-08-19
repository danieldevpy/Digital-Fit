"""Saúde de cada exercício em produção (T-104 / SPEC-020).

`validado` exige "taxa de sessões zero-rep < 20% por uma semana", e até aqui ninguém media
isso — um critério mensurável sem instrumento vira opinião, e promoção por opinião é como o
polichinelo e o agachamento chegaram a `validado`.

## Por que a taxa é sobre as sessões que CHEGARAM AO FIM, e não sobre todas

Uma sessão termina por cinco motivos (`SessionEndReason`), e só dois significam que a análise
correu até o fim:

| motivo | o que aconteceu | o que uma contagem zero diz aqui |
|---|---|---|
| `completed` | os 30 s correram | **a FSM não viu repetição** — é o sintoma do `[A/T-032]` |
| `target_reached` | a meta do modo contado foi atingida | a FSM contou até a N-ésima — ver abaixo |
| `no_data` | 10 s sem frame chegar | câmera, aba fechada, rede — não diz nada sobre contagem |
| `aborted` | quem treina desistiu | nada |
| `timeout` | o TTL da sessão venceu | nada |

Somar os cinco num número só foi exatamente o erro que fez o agachamento parecer quebrado
por semanas (T-133): treze sessões com zero repetição, **todas** `no_data`, lidas como "o
exercício não conta". O agachamento contava. Por isso a taxa desta spec sai das sessões que
chegaram ao fim, e `no_data` aparece **ao lado**, como a segunda métrica que é — alta ali é
problema de captura, e o conserto fica em outro lugar do produto.

Duas leituras, dois donos. Um número só teria um dono errado.

## `target_reached` (T-140): por que entra, e a coluna que ele obrigou a existir

Desde a T-136 uma sessão pode terminar porque a meta de repetições foi atingida, e até a T-140
esse motivo **caía em balde nenhum**: entrava no total e sumia da taxa e da cadência. Um modo
inteiro do produto ficava fora do instrumento que decide promover e rebaixar exercício.

Ele entra em `completas` porque é o bucket "a análise correu até o fim", e uma série que bateu a
meta chegou ao fim de forma mais categórica que os 30 s do modo livre: o fim é a N-ésima
repetição *detectada*, não o relógio.

**E ele quase nunca pode ser zero.** A sessão terminou porque a rep N foi vista, então
`rep_count >= 1` por construção: ele engrossa o denominador da taxa e nunca o numerador — ou
seja, **puxa a taxa para baixo**. Isso é honesto (é uma observação real de que a análise
funcionou), e é justamente por isso que é perigoso: um produto que migre para o modo contado
veria a taxa despencar e pararia de ouvir o alarme, sem nada ter melhorado. Daí a coluna
`atingiu_meta`, impressa ao lado de `completas`: quem lê vê **de que** a taxa é feita. É a mesma
doutrina do `no_data` em coluna separada, aplicada ao problema simétrico.

O zero dele continua sendo contado em `zeradas`, apesar de improvável. Se um dia aparecer, é
sinal de que alguma coisa está errada na meta ou na contagem — e o lugar certo para uma anomalia
é aparecer no alarme, não ser descartada por uma suposição.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from django.db.models import Count, Q, Sum
from django.utils import timezone

from api.models import Exercise, SessionResult

__all__ = [
    "JANELA_PADRAO_DIAS",
    "LIMITE_ZERO",
    "MINIMO_PARA_VEREDITO",
    "ExerciseHealth",
    "coletar",
]

#: Uma semana — a janela que a SPEC-020 nomeia no critério de `validado`.
JANELA_PADRAO_DIAS = 7

#: O limite da SPEC-020: acima disto o exercício não é `validado`.
LIMITE_ZERO = 0.20

#: Abaixo de tantas sessões completas, taxa não é medida — é ruído. Duas sessões com um zero
#: dariam "50%", e rebaixar um exercício por causa disso seria pior que não medir.
MINIMO_PARA_VEREDITO = 5

#: Motivos de fim (espelho de `SessionEndReason`; o servidor grava o texto).
_COMPLETED = "completed"
#: Modo contado: a meta foi atingida (SPEC-023/T-134). Conta como sessão que chegou ao fim.
_TARGET_REACHED = "target_reached"
_NO_DATA = "no_data"

#: Os motivos em que a análise correu até o fim — o denominador da taxa da SPEC-020.
_CHEGOU_AO_FIM = (_COMPLETED, _TARGET_REACHED)
_ABORTED = "aborted"
_TIMEOUT = "timeout"


@dataclass(frozen=True, slots=True)
class ExerciseHealth:
    """O que o banco sabe sobre um exercício na janela pedida."""

    slug: str
    display_name: str
    #: `beta` / `calibrado` / `validado`, ou `None` para slug que não está mais no catálogo.
    maturity: str | None = None
    enabled: bool = True
    #: `False` quando há sessões gravadas de um slug que o catálogo não conhece mais.
    no_catalogo: bool = True

    total: int = 0
    completas: int = 0
    #: Quantas das `completas` terminaram por bater a meta do modo contado (T-140). Coluna
    #: própria porque ela quase nunca é zerada e, portanto, só empurra a taxa para baixo —
    #: sem este número, a diluição não teria como ser vista.
    atingiu_meta: int = 0
    zeradas: int = 0
    sem_dado: int = 0
    abortadas: int = 0
    expiradas: int = 0
    reps: int = 0
    cadencias: list[float] = field(default_factory=list)

    @property
    def taxa_zero(self) -> float | None:
        """Sessões que chegaram ao fim e contaram zero. `None` quando não houve nenhuma.

        Denominador = `completed` + `target_reached` (T-140). Ver o cabeçalho do módulo para o
        porquê de a segunda entrar e para o que a coluna `atingiu_meta` existe para revelar.
        """
        return None if self.completas == 0 else self.zeradas / self.completas

    @property
    def taxa_sem_dado(self) -> float | None:
        """Sessões que morreram por falta de frame. Não entra na taxa da SPEC-020."""
        return None if self.total == 0 else self.sem_dado / self.total

    @property
    def cadencia_mediana(self) -> float | None:
        """Mediana da cadência das sessões que contaram. Mediana e não média: uma sessão de
        cinco repetições em trinta segundos puxa uma média e não move uma mediana."""
        return statistics.median(self.cadencias) if self.cadencias else None

    @property
    def veredito(self) -> str:
        """A leitura da SPEC-020 em uma palavra.

        `poucas` não é meio-termo diplomático: é a diferença entre "medi e está bom" e "não
        medi". Promover ou rebaixar com base em três sessões é decidir no ruído.
        """
        if self.total == 0:
            return "sem sessao"
        if self.completas < MINIMO_PARA_VEREDITO:
            return "poucas"
        taxa = self.taxa_zero
        assert taxa is not None  # completas >= MINIMO_PARA_VEREDITO garante isto
        return "ok" if taxa < LIMITE_ZERO else "atencao"

    def to_dict(self) -> dict[str, Any]:
        return {
            "exercise": self.slug,
            "display_name": self.display_name,
            "maturity": self.maturity,
            "enabled": self.enabled,
            "no_catalogo": self.no_catalogo,
            "total": self.total,
            "completas": self.completas,
            "atingiu_meta": self.atingiu_meta,
            "zeradas": self.zeradas,
            "sem_dado": self.sem_dado,
            "abortadas": self.abortadas,
            "expiradas": self.expiradas,
            "reps": self.reps,
            "taxa_zero": self.taxa_zero,
            "taxa_sem_dado": self.taxa_sem_dado,
            "cadencia_mediana": self.cadencia_mediana,
            "veredito": self.veredito,
        }


def coletar(dias: int = JANELA_PADRAO_DIAS) -> list[ExerciseHealth]:
    """Lê `SessionResult` na janela e devolve uma linha por exercício.

    Ordem: a do catálogo (`ordem`, `slug`), com os slugs órfãos — que existem no banco e não
    no catálogo — no fim. Exercício do catálogo **sem nenhuma sessão aparece mesmo assim**,
    zerado: ausência é resposta, e um exercício que ninguém abriu é notícia tão boa quanto um
    que todo mundo abriu e que não conta.
    """
    inicio = timezone.now() - timedelta(days=dias)
    sessoes = SessionResult.objects.filter(created_at__gte=inicio)

    # Uma linha por (exercício, motivo). O recorte da janela é o que mantém isto barato num
    # banco que cresce sem limite — mesma regra do resumo do painel.
    contagens = (
        sessoes.values("exercise", "reason")
        .annotate(
            n=Count("pk"),
            zeros=Count("pk", filter=Q(rep_count=0)),
            reps=Sum("rep_count"),
        )
        .order_by()
    )

    bruto: dict[str, dict[str, Any]] = {}
    for linha in contagens:
        slug = linha["exercise"]
        acumulado = bruto.setdefault(
            slug,
            {
                "total": 0,
                "completas": 0,
                "atingiu_meta": 0,
                "zeradas": 0,
                "sem_dado": 0,
                "abortadas": 0,
                "expiradas": 0,
                "reps": 0,
            },
        )
        acumulado["total"] += linha["n"]
        acumulado["reps"] += linha["reps"] or 0
        motivo = linha["reason"]
        if motivo in _CHEGOU_AO_FIM:
            acumulado["completas"] += linha["n"]
            # Só o zero de uma sessão que chegou ao fim é zero de CONTAGEM. O das outras é
            # zero de sessão que não chegou lá.
            acumulado["zeradas"] += linha["zeros"]
            if motivo == _TARGET_REACHED:
                acumulado["atingiu_meta"] += linha["n"]
        elif motivo == _NO_DATA:
            acumulado["sem_dado"] += linha["n"]
        elif motivo == _ABORTED:
            acumulado["abortadas"] += linha["n"]
        elif motivo == _TIMEOUT:
            acumulado["expiradas"] += linha["n"]

    # A cadência sai só das sessões que contaram: incluir zeros arrastaria a mediana para
    # baixo com sessões em que ela nem chegou a ser calculada.
    #
    # `target_reached` entra aqui (T-140), e é o dado mais comparável que existe: no modo
    # contado todas as séries têm a mesma meta, então reps/min mede ritmo e não quanto a pessoa
    # aguentou. Deixá-lo de fora faria a mediana de um exercício muito usado no modo contado
    # descrever justamente a minoria das sessões dele.
    cadencias: dict[str, list[float]] = {}
    consulta = sessoes.filter(reason__in=_CHEGOU_AO_FIM, rep_count__gt=0).values_list(
        "exercise", "cadence_rpm"
    )
    for slug, cadencia in consulta:
        cadencias.setdefault(slug, []).append(float(cadencia))

    catalogo = list(Exercise.objects.order_by("ordem", "slug"))
    conhecidos = {exercicio.slug for exercicio in catalogo}

    saude: list[ExerciseHealth] = [
        _linha(
            slug=exercicio.slug,
            display_name=exercicio.display_name,
            maturity=exercicio.maturity,
            enabled=exercicio.enabled,
            no_catalogo=True,
            bruto=bruto.get(exercicio.slug, {}),
            cadencias=cadencias.get(exercicio.slug, []),
        )
        for exercicio in catalogo
    ]
    # Slug gravado que o catálogo não conhece: exercício removido, renomeado, ou sessão vinda
    # da bancada. Some do painel e continua no banco — esconder seria perder o histórico dele.
    saude.extend(
        _linha(
            slug=slug,
            display_name=slug,
            maturity=None,
            enabled=False,
            no_catalogo=False,
            bruto=bruto[slug],
            cadencias=cadencias.get(slug, []),
        )
        for slug in sorted(bruto)
        if slug not in conhecidos
    )
    return saude


def _linha(
    *,
    slug: str,
    display_name: str,
    maturity: str | None,
    enabled: bool,
    no_catalogo: bool,
    bruto: dict[str, Any],
    cadencias: list[float],
) -> ExerciseHealth:
    return ExerciseHealth(
        slug=slug,
        display_name=display_name,
        maturity=maturity,
        enabled=enabled,
        no_catalogo=no_catalogo,
        total=bruto.get("total", 0),
        completas=bruto.get("completas", 0),
        atingiu_meta=bruto.get("atingiu_meta", 0),
        zeradas=bruto.get("zeradas", 0),
        sem_dado=bruto.get("sem_dado", 0),
        abortadas=bruto.get("abortadas", 0),
        expiradas=bruto.get("expiradas", 0),
        reps=bruto.get("reps", 0),
        cadencias=cadencias,
    )
