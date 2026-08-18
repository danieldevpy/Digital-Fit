"""Fogo, meta diária, XP e níveis (SPEC-019, Fase Inicial — T-086).

**Este módulo não faz I/O.** Nenhum import de Django, nenhuma consulta, nenhuma leitura de
relógio: `hoje` é parâmetro, as sessões chegam como lista, o plano chega como número. É a mesma
filosofia da FSM (SPEC-007), e pela mesma razão — a promessa do §Entidade da spec é que
*"recalcular do zero dá o mesmo resultado"*, e uma função que lê o relógio por dentro não pode
provar isso num teste.

Quem faz o I/O é a view (`views.engagement`): uma consulta por usuário, o resultado pronto
guardado em Redis. Cache é otimização; a verdade é esta função.

## As duas leituras que esta implementação fixou, e por quê

A spec se contradiz em dois pontos, e os dois mudam o número que aparece na tela. As decisões
abaixo foram levadas de volta para a SPEC-019 (§Downgrade e §Vocabulário) — aqui fica o porquê,
junto do código que as executa.

**1. Proteção cobre também o dia falho da ponta.** O §Vocabulário dizia "dia falho perdoado *no
meio* de uma sequência", mas o critério de aceite 4 diz apenas *"dia falho com proteção
disponível não apaga o fogo"*. Vale o critério: uma proteção que só agisse entre dois dias
treinados seria **invisível no único momento em que importa**. Quem treinou seg/ter/qua e faltou
na quinta abriria o app na sexta e veria fogo 0 — para vê-lo voltar a 4 só depois de treinar de
novo. Isso não é proteção, é ressurreição retroativa; e ressurreição é exatamente a mecânica
**paga** que a spec deixou na Fase Evolução ("reacender"). Dar de graça, sem querer, a mecânica
que se pretende vender é pior do que a ambiguidade que a causou.

**2. O piso do downgrade é o teto do catálogo, não o plano de agora.** A §Downgrade mandava usar
`max(plano_atual, plano_free)` para meses passados. Para quem foi rebaixado de assinante para
free, `plano_atual` **é** free: `max(1, 1) = 1`, e o critério de aceite 10 — "rebaixar não
encurta sequência que já consumiu 2 proteções em mês anterior" — falha no caso exato que a seção
existe para proteger. A fórmula era a única frase daquela seção que discordava do resto dela.

O conserto tem um custo, e ele é assumido: quem **nunca** assinou também recebe o teto para trás.
Sem histórico de plano por data — que a spec rejeitou explicitamente, para não transformar plano
em série temporal — não há como distinguir "tinha direito" de "não tinha". Das duas imprecisões
possíveis, esta erra para o lado de não apagar fogo de ninguém, que é o lado que a seção inteira
escolheu.
"""

from __future__ import annotations

import bisect
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

__all__ = [
    "ACHIEVEMENTS",
    "FUSO_DO_FOGO",
    "HOLD_VALIDO_MS",
    "LEVELS",
    "METAS",
    "META_PADRAO",
    "PROTECOES_TETO",
    "SCORING_HOLD",
    "SCORING_REPS",
    "XP_EXECUCAO_LIMPA",
    "XP_FORMULA_V",
    "XP_POR_REP",
    "XP_SESSAO_VALIDA",
    "XP_TETO_REPS",
    "Agregados",
    "Conquista",
    "Engajamento",
    "Nivel",
    "Sessao",
    "StreakInfo",
    "catalogo_de_conquistas",
    "chave_de_cache",
    "conquistas",
    "decomposicao_de_xp",
    "dia_sp",
    "dias_ativos",
    "nivel",
    "resumo",
    "sessao_valida",
    "streak",
    "ttl_ate_a_virada",
    "xp_da_sessao",
    "xp_total",
]

#: A virada do dia do fogo. Fixo, para todo mundo, e **divergente da quota** (que conta em UTC,
#: SPEC-016). A spec dedica um parágrafo a isso: quota é contabilidade de carga, fogo é o dia que
#: a pessoa chama de dia — e meia-noite UTC é 21 h no Brasil, o que faria "treinei às 22h" contar
#: para amanhã. Fuso por usuário é Fase Evolução.
FUSO_DO_FOGO = ZoneInfo("America/Sao_Paulo")

#: Versão da fórmula de XP (SPEC-019 §XP). Mudou a fórmula, incrementa **e recalcula tudo** — é
#: derivado, é barato, e evita o museu de pontos incomparáveis. Vai no payload para que qualquer
#: XP exibido saiba dizer sob qual fórmula foi contado.
XP_FORMULA_V = 1

XP_SESSAO_VALIDA = 10
XP_POR_REP = 1
XP_TETO_REPS = 40
XP_EXECUCAO_LIMPA = 10

#: Modalidade de pontuação do exercício (SPEC-021). Entra por **parâmetro** e não por consulta ao
#: catálogo: é o que mantém este módulo testável sem Django. Hoje nenhum exercício é `hold` — a
#: coluna `hold_valid_ms` chega na T-098 —, e o ramo existe escrito e testado para que o dia da
#: chegada seja uma linha de mapa, não uma regra nova.
SCORING_REPS = "reps"
SCORING_HOLD = "hold"

#: Piso de uma sessão `hold` válida (SPEC-019 §Vocabulário / SPEC-021).
HOLD_VALIDO_MS = 10_000

#: Meta diária: sessões válidas por dia. Vocabulário da spec, não configuração — o número que a
#: palavra significa é a mesma coisa no servidor e no anel da tela.
METAS: dict[str, int] = {"casual": 1, "regular": 2, "intenso": 4}
META_PADRAO = "casual"

#: Faixas de nível. As cinco primeiras são as da spec; as demais seguem o mesmo espaçamento.
#: **Nível não tem nome aqui de propósito**: a spec diz "nomes definidos com o produto", e
#: inventar copy dentro de uma task de derivação seria decidir produto por conveniência. A tela
#: mostra "Nível 3" até alguém batizar.
LEVELS: list[int] = [0, 100, 300, 700, 1500, 3000, 5000, 8000, 12000, 20000]

#: Teto de proteções do catálogo de planos (assinatura = 2, SPEC-018 §A). É o piso histórico do
#: §Downgrade — ver a nota 2 do topo deste módulo. Constante e não consulta: o valor de um plano
#: **de hoje** não pode decidir o perdão de um mês que já passou.
PROTECOES_TETO = 2

#: Folga do TTL do cache, em segundos. A chave já carrega a data; a folga só evita que uma
#: diferença de relógio faça a entrada evaporar um segundo antes da virada.
_FOLGA_TTL_S = 60


def dia_sp(quando: datetime) -> date:
    """O dia-calendário de um instante, no fuso do fogo.

    Ingênuo é lido como UTC — é o que o banco guarda (`USE_TZ=True`), e adivinhar outro fuso
    aqui deslocaria o dia de quem treina de noite, que é justamente o caso que o fuso protege.
    """
    if quando.tzinfo is None:
        quando = quando.replace(tzinfo=UTC)
    return quando.astimezone(FUSO_DO_FOGO).date()


@dataclass(frozen=True, slots=True)
class Sessao:
    """Uma sessão como a derivação a enxerga.

    Não é o `SessionResult`: é o recorte dele que o engajamento precisa, e existe para que as
    fixtures sejam listas escritas à mão, sem banco e sem migration (critério de aceite 1). A
    view monta estes objetos a partir de um `values_list` de cinco colunas.
    """

    #: Relógio do **servidor**, em UTC (`SessionResult.created_at`). A conversão para o dia de
    #: São Paulo é da derivação, nunca do armazenamento.
    created_at: datetime
    exercise: str = ""
    rep_count: int = 0
    #: Chega na T-098 (SPEC-021). Zero até lá — e nenhum exercício é `hold` até lá.
    hold_valid_ms: int = 0
    feedback_counts: Mapping[str, int] = field(default_factory=dict)
    scene_warning_counts: Mapping[str, int] = field(default_factory=dict)

    @property
    def limpa(self) -> bool:
        """Sem uma correção de execução e sem um aviso de cena.

        A regra mora aqui, e não em quem monta a `Sessao`, porque ela é a fórmula do bônus de
        XP — deixá-la na consulta faria a fixture testar uma coisa e a produção pontuar outra.
        """
        return not self.feedback_counts and not self.scene_warning_counts

    @property
    def dia(self) -> date:
        return dia_sp(self.created_at)


def sessao_valida(sessao: Sessao, scoring: str = SCORING_REPS) -> bool:
    """Sessão que conta para fogo, meta e XP (SPEC-019 §Vocabulário).

    Zero repetição não conta para nada — senão abrir a câmera por 30 s viraria fazenda de fogo.
    """
    if scoring == SCORING_HOLD:
        return sessao.hold_valid_ms >= HOLD_VALIDO_MS
    return sessao.rep_count >= 1


def _scoring_de(sessao: Sessao, scoring_por_slug: Mapping[str, str] | None) -> str:
    """Modalidade do exercício da sessão. Ausente = `reps`, que é o produto inteiro de hoje."""
    if not scoring_por_slug:
        return SCORING_REPS
    return scoring_por_slug.get(sessao.exercise, SCORING_REPS)


def _validas(sessoes: Iterable[Sessao], scoring_por_slug: Mapping[str, str] | None) -> list[Sessao]:
    return [s for s in sessoes if sessao_valida(s, _scoring_de(s, scoring_por_slug))]


def dias_ativos(
    sessoes: Iterable[Sessao], scoring_por_slug: Mapping[str, str] | None = None
) -> set[date]:
    """Dias-calendário (em SP) com ao menos uma sessão válida."""
    return {sessao.dia for sessao in _validas(sessoes, scoring_por_slug)}


@dataclass(frozen=True, slots=True)
class StreakInfo:
    """O fogo: o de agora, o melhor de todos os tempos, e o que a sequência atual custou."""

    corrente: int
    melhor: int
    protecoes_usadas_mes: int


def _orcamento_do_mes(dia: date, hoje: date, protecoes_mes: int, protecoes_historicas: int) -> int:
    """Quantas proteções valem no mês deste dia (SPEC-019 §Downgrade).

    Mês corrente: o plano de agora — "a assinatura acabou" tem de significar alguma coisa, e o
    que ela significa é que o benefício some **para frente**. Mês passado: o teto do catálogo,
    porque perdão já concedido não é retirado. Ver a nota 2 do topo do módulo.
    """
    if (dia.year, dia.month) == (hoje.year, hoje.month):
        return protecoes_mes
    return max(protecoes_mes, protecoes_historicas)


def _caminhada(
    dias: set[date],
    ancora: date,
    hoje: date,
    protecoes_mes: int,
    protecoes_historicas: int,
) -> tuple[int, dict[tuple[int, int], int]]:
    """Anda para trás a partir de `ancora` e devolve (dias ativos contados, proteções por mês).

    Duas regras governam o passo:

    - **Dia ativo conta**; dia falho consome uma proteção do orçamento do *seu* mês, e a
      sequência morre quando o orçamento do mês acaba. O dia protegido **não** entra na
      contagem: ele não foi treinado, só não interrompeu — "número de dias ativos consecutivos"
      é o que a spec conta.
    - **Hoje nunca é dia falho.** O dia não acabou; cobrar uma proteção por ele faria a pessoa
      pagar às 00h01 por um treino que ainda pode fazer às 22h.
    """
    contados = 0
    usadas: dict[tuple[int, int], int] = {}
    mais_antigo = min(dias)
    dia = ancora

    while dia >= mais_antigo:
        if dia in dias:
            contados += 1
        elif dia != hoje:
            chave = (dia.year, dia.month)
            orcamento = _orcamento_do_mes(dia, hoje, protecoes_mes, protecoes_historicas)
            if usadas.get(chave, 0) >= orcamento:
                break
            usadas[chave] = usadas.get(chave, 0) + 1
        dia -= timedelta(days=1)

    return contados, usadas


def streak(
    dias: set[date],
    hoje: date,
    protecoes_mes: int,
    *,
    protecoes_historicas: int = PROTECOES_TETO,
) -> StreakInfo:
    """Fogo corrente, melhor sequência e proteções gastas no mês corrente.

    `melhor` é calculado ancorando a mesma caminhada em **cada** dia ativo: é literalmente "o
    maior número que o fogo já mostrou". Custa O(dias ativos × vão), e o vão é o intervalo de
    datas do usuário — para um histórico de anos ainda é ruído perto da consulta que o alimenta.
    """
    if not dias:
        return StreakInfo(corrente=0, melhor=0, protecoes_usadas_mes=0)

    corrente, usadas = _caminhada(dias, hoje, hoje, protecoes_mes, protecoes_historicas)
    if corrente == 0:
        # Fogo apagado não gastou proteção nenhuma: o que foi consumido na caminhada não
        # sustentou sequência, e cobrar por isso tiraria do mês seguinte um perdão que ninguém
        # recebeu.
        usadas = {}

    melhor = corrente
    for ancora in dias:
        contados, _ = _caminhada(dias, ancora, hoje, protecoes_mes, protecoes_historicas)
        melhor = max(melhor, contados)

    return StreakInfo(
        corrente=corrente,
        melhor=melhor,
        protecoes_usadas_mes=usadas.get((hoje.year, hoje.month), 0),
    )


def xp_da_sessao(sessao: Sessao, scoring: str = SCORING_REPS) -> int:
    """XP de uma sessão (SPEC-019 §XP, fórmula v1).

    **Só lê o `SessionResult`.** É a regra geral que a spec fixou depois de tirar o bônus de meta
    batida da fórmula: a meta é campo mutável do perfil, e um componente que a lesse faria o XP
    de dias passados mudar quando alguém trocasse a meta hoje. Componente que precise de outra
    fonte vira fato gravado primeiro.
    """
    if not sessao_valida(sessao, scoring):
        return 0

    xp = XP_SESSAO_VALIDA
    xp += min(sessao.rep_count * XP_POR_REP, XP_TETO_REPS)
    if sessao.limpa:
        # O bônus que o Duolingo não tem e nós temos de graça: o feedback engine já mede a forma.
        xp += XP_EXECUCAO_LIMPA
    return xp


def xp_total(sessoes: Iterable[Sessao], scoring_por_slug: Mapping[str, str] | None = None) -> int:
    return sum(xp_da_sessao(s, _scoring_de(s, scoring_por_slug)) for s in sessoes)


def decomposicao_de_xp(sessao: Sessao, scoring: str = SCORING_REPS) -> dict[str, Any]:
    """A conta do XP desta sessão, parcela a parcela (SPEC-019 §Superfícies).

    O relatório mostra "+38 · sessão 10 · reps 18 · limpa 10", e é **onde o bônus de forma
    ensina que forma vale ponto**. A decomposição sai daqui, do mesmo lugar que soma o total,
    porque a alternativa era um espelho da fórmula em TypeScript — e a fórmula é *versionada*
    (`XP_FORMULA_V`), o que garante que um dia ela muda e que um dia só um dos dois lados é
    corrigido. É o `[A/T-051]` esperando para acontecer, com pontos em vez de exercícios.

    Sessão inválida devolve tudo zerado em vez de `None`: a linha some da tela por decisão de
    quem desenha, não por ausência de campo.
    """
    valida = sessao_valida(sessao, scoring)
    base = XP_SESSAO_VALIDA if valida else 0
    reps = min(sessao.rep_count * XP_POR_REP, XP_TETO_REPS) if valida else 0
    limpa = XP_EXECUCAO_LIMPA if valida and sessao.limpa else 0
    return {
        "total": base + reps + limpa,
        "session": base,
        "reps": reps,
        "clean": limpa,
        "formula_v": XP_FORMULA_V,
    }


@dataclass(frozen=True, slots=True)
class Nivel:
    """Nível como apresentação sobre XP total. Sem persistência própria (SPEC-019 §XP)."""

    numero: int
    xp: int
    xp_min: int
    #: `None` no último nível — e é a resposta honesta, não um teto inventado.
    xp_proximo: int | None

    @property
    def progresso(self) -> float:
        """0.0–1.0 dentro da faixa. `1.0` no último nível: não há para onde progredir."""
        if self.xp_proximo is None:
            return 1.0
        vao = self.xp_proximo - self.xp_min
        return 0.0 if vao <= 0 else min(1.0, (self.xp - self.xp_min) / vao)

    def to_dict(self) -> dict[str, Any]:
        return {
            "number": self.numero,
            "xp_min": self.xp_min,
            "xp_next": self.xp_proximo,
            "progress": round(self.progresso, 4),
        }


def nivel(xp: int) -> Nivel:
    """Faixa de `LEVELS` em que este XP cai. Nível 1 começa em zero."""
    indice = max(0, bisect.bisect_right(LEVELS, max(0, xp)) - 1)
    return Nivel(
        numero=indice + 1,
        xp=max(0, xp),
        xp_min=LEVELS[indice],
        xp_proximo=LEVELS[indice + 1] if indice + 1 < len(LEVELS) else None,
    )


@dataclass(frozen=True, slots=True)
class Agregados:
    """O que os predicados de conquista leem (SPEC-019 §Conquistas).

    Um objeto e não os `Sessao` crus porque os predicados são **puros e baratos por
    construção**: cada um é uma comparação, e nenhum pode varrer a lista de sessões por conta
    própria. Sem esta fronteira, uma conquista nova acrescentaria uma passada sobre o histórico
    inteiro sem ninguém notar — e são todas calculadas a cada leitura.
    """

    sessoes_validas: int = 0
    melhor_streak: int = 0
    reps_totais: int = 0
    #: Maior acumulado num MESMO exercício. `centena` pergunta por exercício, não no total.
    reps_no_melhor_exercicio: int = 0
    sessoes_limpas: int = 0
    #: Maior sequência de dias seguidos batendo a meta. Ver a nota em `ACHIEVEMENTS`.
    melhor_sequencia_de_meta: int = 0
    #: `True` quando o catálogo já traz categoria por exercício (SPEC-020/T-090). Enquanto for
    #: `False`, as conquistas que dependem dela ficam desligadas em vez de nascerem falsas.
    tem_categorias: bool = False


@dataclass(frozen=True, slots=True)
class Conquista:
    """Uma conquista do catálogo: slug + predicado. Sem tabela: a lista de alguém é
    `conquistas(agregados)`.

    **Sem nome nem descrição** (SPEC-025, T-145): eram texto fixo em português dentro deste
    módulo puro, e este módulo promete não saber de locale nenhum (ver o topo do arquivo). O
    texto saiu para `server/api/i18n/messages.<locale>.yaml`, resolvido por
    `engagement_cache._derivar` na hora de montar o corpo de `GET /api/engagement` — o slug é o
    contrato entre os dois lados, a mesma separação que já valia para o `code` do feedback.
    """

    slug: str
    predicado: Callable[[Agregados], bool]

    def to_dict(self, *, ganha: bool) -> dict[str, Any]:
        return {"slug": self.slug, "earned": ganha}


#: Catálogo v1 (SPEC-019 §Conquistas). **Em código, não em tabela**: um predicado é lógica, e
#: lógica criada por formulário não tem teste nem fixture (mesmo argumento da SPEC-018 P3 para
#: limiar de FSM).
#:
#: A ordem é a de exibição na galeria, e vai do fácil ao difícil de propósito: uma vitrine que
#: abrisse com `milheiro` apagado diria a quem acabou de chegar que o jogo não é para ela.
#:
#: **Sobre `semana-cheia`**: o predicado lê a meta, que é campo mutável do perfil. A spec o
#: nomeia assim ("a meta ... vale como gatilho da conquista `semana-cheia`"), e por isso ele
#: está aqui — mas isso torna esta a única conquista **revogável** do catálogo: subir a meta de
#: casual para intenso pode apagá-la. Registrado como Descoberta `[T-089]`.
ACHIEVEMENTS: tuple[Conquista, ...] = (
    Conquista("primeira-sessao", lambda a: a.sessoes_validas >= 1),
    Conquista("fogo-7", lambda a: a.melhor_streak >= 7),
    Conquista("semana-cheia", lambda a: a.melhor_sequencia_de_meta >= 7),
    Conquista("centena", lambda a: a.reps_no_melhor_exercicio >= 100),
    Conquista("sem-reparo", lambda a: a.sessoes_limpas >= 10),
    Conquista("fogo-30", lambda a: a.melhor_streak >= 30),
    Conquista("milheiro", lambda a: a.reps_totais >= 1000),
)


def conquistas(agregados: Agregados) -> list[str]:
    """Os slugs que esta pessoa já tem. Derivado, sem tabela e sem "notificado em"."""
    return [c.slug for c in ACHIEVEMENTS if c.predicado(agregados)]


def catalogo_de_conquistas(agregados: Agregados) -> list[dict[str, Any]]:
    """O catálogo **inteiro**, cada uma dizendo se foi ganha.

    Inteiro e não só as ganhas: a galeria do Perfil desenha as bloqueadas apagadas, e é isso que
    transforma a tela num objetivo em vez de um troféu. Mandar só as ganhas obrigaria o cliente
    a ter a lista completa escrita nele — e aí o catálogo estaria em dois lugares.
    """
    ganhas = set(conquistas(agregados))
    return [c.to_dict(ganha=c.slug in ganhas) for c in ACHIEVEMENTS]


@dataclass(frozen=True, slots=True)
class Engajamento:
    """Corpo do `GET /api/engagement`, já derivado."""

    streak: int
    melhor_streak: int
    protecoes_usadas_mes: int
    protecoes_mes: int
    treinou_hoje: bool
    sessoes_hoje: int
    meta: str
    meta_alvo: int
    meta_batida_hoje: bool
    xp: int
    nivel: Nivel
    #: Catálogo INTEIRO, cada uma dizendo se foi ganha — a galeria desenha as bloqueadas
    #: apagadas, e é isso que transforma a tela num objetivo em vez de um troféu (T-089).
    conquistas: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Chaves em inglês, como todo corpo de API deste projeto (`to_report`, `to_dict`)."""
        return {
            "streak": self.streak,
            "best_streak": self.melhor_streak,
            "protections_used_month": self.protecoes_usadas_mes,
            "protections_month": self.protecoes_mes,
            "today_active": self.treinou_hoje,
            "sessions_today": self.sessoes_hoje,
            "goal": self.meta,
            "goal_target": self.meta_alvo,
            "goal_done_today": self.meta_batida_hoje,
            "xp": self.xp,
            "xp_formula_v": XP_FORMULA_V,
            "level": self.nivel.to_dict(),
            "achievements": self.conquistas,
        }


def _melhor_sequencia_de_meta(por_dia: Mapping[date, int], alvo: int) -> int:
    """Maior corrida de dias seguidos em que a meta foi batida.

    Sem proteção: aqui não há perdão nenhum a conceder — a conquista é sobre ter feito, não
    sobre não ter faltado. Proteção existe para o fogo, que mede *voltar*.
    """
    batidos = sorted(dia for dia, quantas in por_dia.items() if quantas >= alvo)
    melhor = 0
    corrente = 0
    anterior: date | None = None
    for dia in batidos:
        corrente = (
            corrente + 1 if anterior is not None and dia - anterior == timedelta(days=1) else 1
        )
        melhor = max(melhor, corrente)
        anterior = dia
    return melhor


def _agregar(validas: list[Sessao], *, melhor_streak: int, alvo: int) -> Agregados:
    """Uma passada só sobre as sessões válidas, alimentando todos os predicados."""
    por_exercicio: dict[str, int] = {}
    por_dia: dict[date, int] = {}
    reps_totais = 0
    limpas = 0

    for sessao in validas:
        reps_totais += sessao.rep_count
        por_exercicio[sessao.exercise] = por_exercicio.get(sessao.exercise, 0) + sessao.rep_count
        por_dia[sessao.dia] = por_dia.get(sessao.dia, 0) + 1
        if sessao.limpa:
            limpas += 1

    return Agregados(
        sessoes_validas=len(validas),
        melhor_streak=melhor_streak,
        reps_totais=reps_totais,
        reps_no_melhor_exercicio=max(por_exercicio.values(), default=0),
        sessoes_limpas=limpas,
        melhor_sequencia_de_meta=_melhor_sequencia_de_meta(por_dia, alvo),
    )


def resumo(
    sessoes: Iterable[Sessao],
    *,
    hoje: date,
    protecoes_mes: int,
    meta: str = META_PADRAO,
    scoring_por_slug: Mapping[str, str] | None = None,
    protecoes_historicas: int = PROTECOES_TETO,
) -> Engajamento:
    """A derivação inteira, de uma vez. É o que a view serializa.

    Uma função só porque os números se olham: a meta do dia conta as *mesmas* sessões válidas
    que acendem o fogo, e dois caminhos para "sessão válida de hoje" acabariam discordando no
    dia em que só um deles fosse corrigido.
    """
    validas = _validas(sessoes, scoring_por_slug)
    dias = {s.dia for s in validas}
    hoje_validas = sum(1 for s in validas if s.dia == hoje)

    info = streak(dias, hoje, protecoes_mes, protecoes_historicas=protecoes_historicas)
    alvo = METAS.get(meta, METAS[META_PADRAO])
    pontos = sum(xp_da_sessao(s, _scoring_de(s, scoring_por_slug)) for s in validas)
    ganhas = catalogo_de_conquistas(_agregar(validas, melhor_streak=info.melhor, alvo=alvo))

    return Engajamento(
        streak=info.corrente,
        melhor_streak=info.melhor,
        protecoes_usadas_mes=info.protecoes_usadas_mes,
        protecoes_mes=protecoes_mes,
        treinou_hoje=hoje in dias,
        sessoes_hoje=hoje_validas,
        meta=meta if meta in METAS else META_PADRAO,
        meta_alvo=alvo,
        meta_batida_hoje=hoje_validas >= alvo,
        xp=pontos,
        nivel=nivel(pontos),
        conquistas=ganhas,
    )


def chave_de_cache(user_id: int | str, hoje: date) -> str:
    """`df:eng:{user}:{data_sp}` — a chave que a spec nomeia, e a data nela não é detalhe.

    Uma chave sem data seria invalidada só por escrita nova, e o payload inteiro (`streak`,
    `today_active`, `goal_done_today`) muda **sozinho à meia-noite**, sem nenhuma escrita para
    disparar signal. Quem treinou às 23h50 e abrisse o app às 00h05 veria o fogo do dia anterior
    e a meta marcada como batida — e continuaria vendo até treinar de novo, ou seja, exatamente
    até deixar de precisar da informação.
    """
    return f"df:eng:{user_id}:{hoje.isoformat()}"


def ttl_ate_a_virada(agora: datetime) -> int:
    """Segundos até a meia-noite seguinte em São Paulo, mais folga."""
    if agora.tzinfo is None:
        agora = agora.replace(tzinfo=UTC)
    local = agora.astimezone(FUSO_DO_FOGO)
    virada = datetime.combine(
        local.date() + timedelta(days=1), datetime.min.time(), tzinfo=FUSO_DO_FOGO
    )
    return max(1, int((virada - local).total_seconds()) + _FOLGA_TTL_S)
