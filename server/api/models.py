"""Persistência da API (SPEC-010, SPEC-011 e SPEC-018).

Tabelas com papéis bem distintos:

- `SessionResult` — o relatório consolidado, escrito pelo **report-builder** a partir dos
  eventos (SPEC-010). Não sabe de usuário e não pode saber: ele é derivável 100% por replay
  do stream, e um replay não conhece quem estava logado.
- `SessionClaim` — de quem é a sessão (SPEC-011). Escrita pela **API** na admissão, que é o
  único momento em que o dono é conhecido. Tabela separada justamente para manter a de cima
  replayável.
- `User` — conta de e-mail e senha (SPEC-011).
- `Plan` e `SiteConfig` — configuração de **negócio**, editável no painel sem deploy
  (SPEC-018). Não confundir com as outras duas naturezas: infra é variável de ambiente, e
  limiar calibrado é constante em código com bancada (SPEC-018 P3). Quem lê estas duas é
  `api/config.py`, nunca um worker (P1).

A sessão **em andamento** continua em Redis com TTL (`api/sessions.py`); o Postgres guarda o
que sobrevive ao fim dela.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models

from api.i18n import LOCALES, SOURCE_LOCALE

__all__ = [
    "MATURITY_RANK",
    "Category",
    "DailyGoal",
    "Exercise",
    "ExerciseGuideStep",
    "ExerciseGuideStepTranslation",
    "ExerciseTranslation",
    "MainAngle",
    "Maturity",
    "Plan",
    "PlanTranslation",
    "SessionClaim",
    "SessionResult",
    "SiteConfig",
    "User",
]

#: Idiomas que uma linha de tradução pode assumir: todo `LOCALES` exceto a própria fonte
#: (SPEC-025 §Tabela de tradução, T-146). As colunas de `Exercise`/`Plan`/`ExerciseGuideStep`
#: JÁ SÃO o `SOURCE_LOCALE` — uma linha de tradução em `pt-BR` seria o dado duplicado dentro de
#: si mesmo. Terceiro idioma entra aqui de graça: é o `LOCALES` de `api.i18n` crescendo uma
#: tupla, não uma migration de vocabulário.
TRANSLATABLE_LOCALE_CHOICES: list[tuple[str, str]] = [
    (locale, locale) for locale in LOCALES if locale != SOURCE_LOCALE
]


class Maturity(models.TextChoices):
    """Escada de maturidade de um exercício (SPEC-020).

    Vive aqui, e não como tabela, porque é **vocabulário de contrato**: a trilha decide o que
    aceita por ele e o plano decide o que mostra por ele. Nível novo é commit, com os dois
    consumidores revisados junto — um nível criado por formulário seria um estado que ninguém
    sabe comparar.

    A ordem da declaração é a ordem de confiança (`beta` < `calibrado` < `validado`) e é o que
    `Plan.min_maturity` compara; ver `MATURITY_RANK` abaixo.
    """

    BETA = "beta", "Beta (só gerador sintético)"
    CALIBRADO = "calibrado", "Calibrado (corpus real — Laboratório 🧪)"
    VALIDADO = "validado", "Validado (paridade + produção)"


#: Confiança crescente. Fora da classe porque um atributo dentro de `TextChoices` viraria um
#: membro do enum. Dicionário e não `IntegerChoices` porque o valor guardado no banco precisa
#: continuar legível numa consulta de suporte ("por que este some para o Free?").
MATURITY_RANK: dict[str, int] = {
    Maturity.BETA.value: 0,
    Maturity.CALIBRADO.value: 1,
    Maturity.VALIDADO.value: 2,
}


class Category(models.TextChoices):
    """Eixo de navegação do catálogo (SPEC-020 §Categorias).

    **Vocabulário em código, e isto contradiz a SPEC-018 §B de propósito** — ela listava
    `category` entre os campos de apresentação editáveis no painel. Não é apresentação: as
    conquistas da SPEC-019 e o mix por objetivo da SPEC-022 consomem estes *slugs*. Uma
    categoria criada por formulário quebraria os dois consumidores em silêncio, e o sintoma
    seria uma conquista que nunca dispara.

    O que continua editável é o que é mesmo apresentação: o nome de exibição do exercício, a
    cor do dot, a ordem. Categoria nova é commit, com os consumidores revisados junto.
    """

    CARDIO = "cardio", "Cardio"
    FORCA = "forca", "Força"
    CORE = "core", "Core"
    MOBILIDADE = "mobilidade", "Mobilidade"


class DailyGoal(models.TextChoices):
    """Quanto a pessoa quer treinar por dia (SPEC-019 §Vocabulário).

    Escolha do usuário e **gratuita**: a meta mede *quanto*, o fogo mede *voltar*. As duas não
    se amarram de propósito — quem pôs "intenso" e fez uma sessão mantém o fogo e vê a meta
    incompleta, porque exercício físico tem dia de corpo cansado e uma meta ambiciosa não pode
    queimar a constância.

    Os rótulos citam o número, mas quem **decide** o número é `engagement.METAS`: o alvo é
    vocabulário da derivação, não configuração de banco. Um teste cobra que os dois conjuntos de
    chaves não divirjam — se alguém acrescentar um nível aqui e esquecer lá, a meta cairia
    silenciosamente no default.
    """

    CASUAL = "casual", "Casual (1 sessão por dia)"
    REGULAR = "regular", "Regular (2 sessões por dia)"
    INTENSO = "intenso", "Intenso (4 sessões por dia)"


class MainAngle(models.TextChoices):
    """Qual ângulo a barra de métricas mostra ao vivo (T-044).

    `none` não é ausência de dado: é a afirmação de que, para este exercício, **nenhum ângulo
    lido no plano da imagem diz a verdade**. No agachamento o joelho viaja para a frente e a
    câmera frontal lê ~133° onde o corpo faz 80° (medido na T-052) — mostrar esse número seria
    pior que mostrar `--`.
    """

    ARM_ABDUCTION = "arm_abduction", "Abdução de braço"
    NONE = "none", "Nenhum (mostra --)"


class RecommendedOrientation(models.TextChoices):
    """Em que orientação de celular ESTE exercício rende (SPEC-027 §E).

    Vocabulário em código pelo mesmo motivo de `Category`: quem consome é a tela, comparando
    com a orientação medida do aparelho. Um valor criado por formulário viraria uma
    recomendação que nunca bate com nada e não avisa ninguém.

    O catálogo já sabia disso em **texto solto** — o `scene_tip` diz "celular deitado no chão,
    de lado" para flexão e abdominal. Texto serve para a pessoa ler; não serve para a tela
    comparar. Este campo é a mesma informação em forma consultável, e os dois convivem: o
    `scene_tip` continua explicando ONDE o celular vai, este diz COMO ele fica.

    `QUALQUER` é o default e não é omissão: é a afirmação de que, para este exercício, as duas
    orientações servem — e é o valor certo para a maioria dos exercícios em pé.
    """

    RETRATO = "retrato", "Em pé (retrato)"
    PAISAGEM = "paisagem", "Deitado (paisagem)"
    QUALQUER = "qualquer", "Tanto faz"


class Plan(models.Model):
    """O que cada tipo de conta pode (SPEC-018 §A + SPEC-016).

    **O anônimo é um plano** (`slug="anon"`), e não um caminho de código à parte. Até aqui o
    trial vivia num módulo próprio porque era o único limite que existia; com esta tabela ele
    passa a ser o plano de entrada do funil — mesmo campo de limite, mesma mensagem de recusa,
    um resolvedor só. O que continua diferente é a **chave do contador** (`trial:{device}:{dia}`
    para anônimo, `df:quota:{user}:{dia}` para logado): a identidade do contado muda, a regra não.

    `is_default` é o plano de quem tem conta e não tem FK — ou seja, `free`. O `anon` nunca é
    default: ele é escolhido pela *ausência* de usuário, não pela ausência de plano.

    Colunas tipadas e não chave-valor (`Config(key, value)`): EAV dispensaria migration, mas
    abriria mão de validação, de tipo e de legibilidade, e este projeto está do lado da
    validação em todas as decisões anteriores. O preço — uma migration por capacidade nova — é
    exatamente o momento em que alguém deveria pensar no que está criando. O `flags` JSON existe
    para o booleano cosmético que nasce e morre em duas semanas.
    """

    slug = models.SlugField(max_length=32, unique=True)
    nome = models.CharField(max_length=60)
    is_default = models.BooleanField(
        default=False,
        help_text="Plano de quem tem conta e não tem plano atribuído. Exatamente um.",
    )
    ordem = models.PositiveSmallIntegerField(default=0)

    daily_sessions = models.PositiveSmallIntegerField(
        default=0, help_text="Sessões por dia. 0 = ilimitado."
    )
    session_min_s = models.PositiveSmallIntegerField(default=30)
    session_max_s = models.PositiveSmallIntegerField(default=30)
    countdown_max_s = models.PositiveSmallIntegerField(default=10)
    allow_cloud = models.BooleanField(default=True)
    history_limit = models.PositiveSmallIntegerField(default=50)
    kcal_accumulation = models.BooleanField(default=False)
    effects_enabled = models.BooleanField(default=False)

    #: Dias falhos perdoados por mês-calendário (SPEC-019). Coluna aqui, cálculo do fogo lá:
    #: capacidade é dado, derivação é função pura.
    streak_protections_month = models.PositiveSmallIntegerField(default=0)
    #: Maturidade mínima visível para este plano (SPEC-020). `validado` é o piso do produto;
    #: `calibrado` é o Laboratório do assinante. `beta` NUNCA é liberado por plano — é
    #: ferramenta de dev, atrás de `is_admin`, e por isso não é opção aqui.
    min_maturity = models.CharField(
        max_length=12,
        choices=[
            (Maturity.VALIDADO.value, Maturity.VALIDADO.label),
            (Maturity.CALIBRADO.value, Maturity.CALIBRADO.label),
        ],
        default=Maturity.VALIDADO,
    )
    #: Card Treino do Dia completo (SPEC-022). Coluna e não `plan.slug == "subscriber"` num
    #: `if` de view: decisão comercial que mora no código precisa de deploy para mudar de ideia.
    daily_workout = models.BooleanField(default=False)

    quota_message = models.TextField(
        blank=True, help_text="Mensagem da recusa por quota deste plano."
    )
    flags = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "plan"
        ordering = ["ordem", "slug"]
        verbose_name = "plano"
        verbose_name_plural = "planos"

    def __str__(self) -> str:
        return f"{self.nome} ({self.slug})"

    def clean(self) -> None:
        """Validação de consequência (SPEC-018 §Sobre o limite do admin).

        O painel não sabe que uma edição tem consequência: nada nele impede desligar o produto
        para todo mundo às 3 h da manhã. Estas faixas são a parte que dá para comprar barato —
        não substituem o P2 (default do código como piso), somam a ele.
        """
        erros: dict[str, str] = {}
        if self.session_min_s > self.session_max_s:
            erros["session_min_s"] = "a duração mínima não pode passar da máxima."
        if not 5 <= self.session_min_s <= 600:
            erros["session_min_s"] = "fora da faixa plausivel (5 a 600 s)."
        if not 5 <= self.session_max_s <= 600:
            erros["session_max_s"] = "fora da faixa plausivel (5 a 600 s)."
        if self.countdown_max_s > 60:
            erros["countdown_max_s"] = "preparação acima de 60 s seguraria vaga sem treinar."
        if erros:
            raise ValidationError(erros)


class PlanTranslation(models.Model):
    """Tradução de `Plan.nome`/`Plan.quota_message` (SPEC-025 §Tabela de tradução, T-146).

    `Plan` continua sendo o pt-BR — nada migra para cá. Uma linha aqui é "a versão neste
    idioma", nunca a fonte. Campo em branco não é "traduzido como vazio": é "sem tradução
    ainda", e `config.config_payload` cai para a coluna base do `Plan` nesse caso — nunca em
    branco, nunca em chave crua (critério 4 da spec). É a mesma regra do docstring de `Plan`
    ("colunas tipadas e não chave-valor"): um `JSONField` aqui contradiria a própria decisão que
    este projeto já tomou.
    """

    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="translations")
    locale = models.CharField(max_length=8, choices=TRANSLATABLE_LOCALE_CHOICES)

    nome = models.CharField(max_length=60, blank=True)
    quota_message = models.TextField(blank=True)

    class Meta:
        db_table = "plan_translation"
        constraints = [
            models.UniqueConstraint(fields=["plan", "locale"], name="uniq_plan_translation_locale")
        ]
        ordering = ["plan_id", "locale"]
        verbose_name = "tradução de plano"
        verbose_name_plural = "traduções de plano"

    def __str__(self) -> str:
        return f"{self.plan.slug} · {self.locale}"

    def clean(self) -> None:
        if self.locale not in dict(TRANSLATABLE_LOCALE_CHOICES):
            raise ValidationError(
                {
                    "locale": (
                        f"{self.locale!r} nao e um idioma traduzivel "
                        f"(a fonte, {SOURCE_LOCALE!r}, nao tem linha propria aqui)."
                    )
                }
            )


class Exercise(models.Model):
    """A **apresentação** de um exercício (SPEC-018 §B). A lógica continua em código.

    O catálogo estava partido em dois: o registro autoritativo (`EXERCISES`, slug → classe da
    FSM, em `workers/analysis_worker/exercises/base.py`) e a apresentação
    (`web/src/session/catalog.ts`). O BACKLOG registrou o efeito em `[A/T-051]`: *"o catálogo do
    cliente e o registro do servidor podem divergir sem ninguém ver"*. Esta tabela é a metade
    que vira dado — nome, dica, imagem, ordem, quem pode ver — e o `GET /api/config` é onde o
    cliente para de ser fonte da verdade sobre o que existe.

    A FSM **não** entra aqui: é lógica, tem fixture e teste, e um limiar mudado por formulário
    não tem nem um nem outro (SPEC-018 P3).
    """

    slug = models.SlugField(max_length=40, unique=True)
    display_name = models.CharField(max_length=60)
    category = models.CharField(max_length=16, choices=Category.choices, default=Category.CARDIO)
    muscle_group = models.CharField(max_length=60, blank=True)
    default_tip = models.TextField(
        blank=True, help_text="Estado vazio do card do treinador — ele nunca fica sem texto."
    )
    main_angle = models.CharField(max_length=16, choices=MainAngle.choices, default=MainAngle.NONE)
    #: Em que orientação este exercício rende (SPEC-027 §E). Orienta, nunca bloqueia.
    orientacao_recomendada = models.CharField(
        max_length=10,
        choices=RecommendedOrientation.choices,
        default=RecommendedOrientation.QUALQUER,
        verbose_name="orientação recomendada",
        help_text=(
            "Aparece como conselho na pré-configuração quando o aparelho está na outra "
            "orientação. Nunca impede treinar."
        ),
    )
    demo_img = models.CharField(max_length=200, blank=True)
    dot_color = models.CharField(max_length=9, default="#34d399")
    #: Como montar a cena para ESTE exercício (SPEC-015 / SPEC-020 Tier C).
    #:
    #: Era uma frase fixa na tela do Guia — "celular apoiado na vertical, uns 2 metros" — o que
    #: é verdade para quem treina em pé e mentira para quem vai fazer flexão com o celular
    #: deitado no chão. Instrução de cena errada não é detalhe de texto: é a diferença entre o
    #: worker enxergar o corpo e a sessão inteira sair zerada. Vazio cai na frase de sempre.
    scene_tip = models.TextField(
        blank=True, help_text="Vazio usa a frase padrão (em pé, celular na vertical, 2 m)."
    )
    #: A palavra que aparece na URL da página pública, em pt-BR (SPEC-026 §Escopo, T-165).
    #:
    #: **Separada do `slug` de propósito.** Aquele é a chave do registro do servidor
    #: (`EXERCISES`), é contrato entre cliente, admissão e worker, e é em inglês porque o código
    #: é. Esta é endereço público, e a razão de a página existir é que ninguém procura "Digital
    #: Fit" — procuram "agachamento". A palavra na URL é sinal de busca, e o `slug` técnico não
    #: pode servir aos dois papéis sem que mudar um quebre o outro.
    #:
    #: Vazio cai no `slug` — é o que faz esta coluna nascer sem migração de dados e sem página
    #: quebrada. Editar depois de a página estar indexada **troca a URL** e perde o que ela
    #: acumulou: é edição de operação, não de texto (ver o aviso no painel).
    url_slug = models.SlugField(
        max_length=60,
        blank=True,
        verbose_name="slug da URL pública",
        help_text="Vazio usa o slug técnico. Mudar troca o endereço de uma página já indexada.",
    )
    ordem = models.PositiveSmallIntegerField(default=0)
    enabled = models.BooleanField(
        default=True, help_text="Desligado some do catálogo E a admissão passa a recusar."
    )
    min_plan = models.ForeignKey(
        "api.Plan",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="exclusive_exercises",
        help_text="Vazio = todo mundo vê. Preenchido = exclusivo deste plano em diante (ordem).",
    )

    #: Insumo do kcal (SPEC-016/017): valor de tabela (Compendium), uma casa decimal, sem
    #: promessa de precisão individual.
    met = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    #: O ritmo em que o `met` acima vale, em repetições por minuto (SPEC-016, T-128).
    #:
    #: O MET de tabela não é um número solto: ele descreve o gasto **a uma intensidade**, e
    #: para um exercício contado por repetição essa intensidade é uma cadência. Sem este campo
    #: não dá para converter MET (por minuto) em caloria por repetição — e foi por não ter esta
    #: coluna que a T-063 acabou faturando tempo de tela em vez de esforço.
    #:
    #: Fica aqui, e não como constante no cliente, pela mesma razão que o `met`: é propriedade
    #: do movimento (20 rpm é rápido para agachamento e lento para polichinelo), e catálogo em
    #: código é o `[A/T-051]` recomeçando. `0` = desconhecido, e aí o card mostra `--`.
    ref_cadence_rpm = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="cadência de referência (rep/min)",
        help_text="Ritmo em que o MET acima vale. 0 = desconhecido (o app mostra '--').",
    )
    #: Quão provado está (SPEC-020). Coluna aqui, **regra de visibilidade na T-090**: esta task
    #: só a carrega até o cliente. Nasce junto para não fazer duas migrations no mesmo modelo.
    maturity = models.CharField(max_length=12, choices=Maturity.choices, default=Maturity.BETA)

    class Meta:
        db_table = "exercise"
        ordering = ["ordem", "slug"]
        verbose_name = "exercício"
        verbose_name_plural = "exercícios"

    def __str__(self) -> str:
        return f"{self.display_name} ({self.slug})"

    def clean(self) -> None:
        """Trava obrigatória da SPEC-018 §B: `slug` só salva se existir em `EXERCISES`.

        Sem isto o painel passa a poder cadastrar um exercício que a admissão rejeita — um botão
        na tela que não funciona, criado por quem achava que estava cadastrando um exercício. O
        import é local porque `workers` não é dependência de importação do módulo de modelos, e
        um import no topo faria o `models.py` puxar o analisador inteiro.
        """
        from workers.analysis_worker.exercises import EXERCISES

        if self.slug and self.slug not in EXERCISES:
            disponiveis = ", ".join(sorted(EXERCISES)) or "nenhum"
            raise ValidationError(
                {
                    "slug": (
                        f"{self.slug!r} nao existe no registro do servidor. "
                        f"Um exercicio nasce em codigo (FSM + fixtures) e so entao aparece aqui. "
                        f"Disponiveis: {disponiveis}."
                    )
                }
            )


class ExerciseTranslation(models.Model):
    """Tradução dos campos de apresentação de `Exercise` (SPEC-025 §Tabela de tradução, T-146).

    `display_name`, `muscle_group`, `default_tip` e `scene_tip` em `Exercise` JÁ SÃO o pt-BR —
    nada migra para cá. Mesma regra do `PlanTranslation`: campo em branco é "sem tradução
    ainda", não "traduzido como vazio"; quem lê (`config.exercises_for`) cai para a coluna base
    quando encontra um branco, e `manage.py i18n_status` é quem torna esse buraco visível antes
    do release, em vez de deixar o inglês mostrar português em silêncio.
    """

    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name="translations")
    locale = models.CharField(max_length=8, choices=TRANSLATABLE_LOCALE_CHOICES)

    display_name = models.CharField(max_length=60, blank=True)
    muscle_group = models.CharField(max_length=60, blank=True)
    default_tip = models.TextField(blank=True)
    scene_tip = models.TextField(blank=True)
    #: O endereço público deste exercício NESTE idioma (T-165). Mesma regra de fallback dos
    #: campos acima: branco cai para `Exercise.url_slug`, que por sua vez cai para o `slug`.
    #: `/exercicios/agachamento/` e `/en/exercises/squat/` são a mesma página em dois idiomas —
    #: e é a tradução do endereço, não só a do texto, que faz a busca em inglês achar a versão
    #: inglesa.
    url_slug = models.SlugField(max_length=60, blank=True, verbose_name="slug da URL pública")

    class Meta:
        db_table = "exercise_translation"
        constraints = [
            models.UniqueConstraint(
                fields=["exercise", "locale"], name="uniq_exercise_translation_locale"
            )
        ]
        ordering = ["exercise_id", "locale"]
        verbose_name = "tradução de exercício"
        verbose_name_plural = "traduções de exercício"

    def __str__(self) -> str:
        return f"{self.exercise.slug} · {self.locale}"

    def clean(self) -> None:
        if self.locale not in dict(TRANSLATABLE_LOCALE_CHOICES):
            raise ValidationError(
                {
                    "locale": (
                        f"{self.locale!r} nao e um idioma traduzivel "
                        f"(a fonte, {SOURCE_LOCALE!r}, nao tem linha propria aqui)."
                    )
                }
            )


class ExerciseGuideStep(models.Model):
    """Passos do exemplo guiado (SPEC-015). Inline no painel, nunca tela própria."""

    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name="guide_steps")
    ordem = models.PositiveSmallIntegerField(default=0)
    img = models.CharField(max_length=200, blank=True)
    texto = models.TextField()

    class Meta:
        db_table = "exercise_guide_step"
        ordering = ["ordem", "pk"]
        verbose_name = "passo do guia"
        verbose_name_plural = "passos do guia"

    def __str__(self) -> str:
        return f"{self.exercise.slug} #{self.ordem}"


class ExerciseGuideStepTranslation(models.Model):
    """Tradução de `ExerciseGuideStep.texto` (SPEC-025 §Tabela de tradução, T-146).

    FK direta ao passo, não ao exercício: um passo é a unidade que se traduz, e a ordem dos
    passos pode variar sem que a tradução perca a referência. `texto` em branco cai para o
    `ExerciseGuideStep.texto` correspondente — a mesma regra de fallback das outras duas tabelas
    desta task.

    O admin não aninha `TabularInline` dentro de `TabularInline`: por isso este modelo aparece
    como inline em `ExerciseGuideStepAdmin` (tela própria, registrada só para hospedar esta
    tradução — ver `api/admin.py`), e não dentro do inline de passos que já vive em
    `ExerciseAdmin`.
    """

    guide_step = models.ForeignKey(
        ExerciseGuideStep, on_delete=models.CASCADE, related_name="translations"
    )
    locale = models.CharField(max_length=8, choices=TRANSLATABLE_LOCALE_CHOICES)

    texto = models.TextField(blank=True)

    class Meta:
        db_table = "exercise_guide_step_translation"
        constraints = [
            models.UniqueConstraint(
                fields=["guide_step", "locale"], name="uniq_guide_step_translation_locale"
            )
        ]
        ordering = ["guide_step_id", "locale"]
        verbose_name = "tradução de passo do guia"
        verbose_name_plural = "traduções de passo do guia"

    def __str__(self) -> str:
        return f"{self.guide_step} · {self.locale}"

    def clean(self) -> None:
        if self.locale not in dict(TRANSLATABLE_LOCALE_CHOICES):
            raise ValidationError(
                {
                    "locale": (
                        f"{self.locale!r} nao e um idioma traduzivel "
                        f"(a fonte, {SOURCE_LOCALE!r}, nao tem linha propria aqui)."
                    )
                }
            )


class SiteConfig(models.Model):
    """Parâmetros globais que não dependem de plano (SPEC-018 §D).

    Singleton por convenção (`pk=1`, garantido pelo `save`): a alternativa — uma linha por
    ambiente — só faria sentido se um processo servisse dois ambientes, o que não acontece e
    não deve passar a acontecer sem ADR.
    """

    cloud_slots = models.PositiveSmallIntegerField(default=3)
    cloud_grace_ms = models.PositiveIntegerField(default=15_000)
    ticket_ttl_s = models.PositiveSmallIntegerField(default=45)
    default_duration_s = models.PositiveSmallIntegerField(default=30)
    default_countdown_s = models.PositiveSmallIntegerField(default=3)

    series_min = models.PositiveSmallIntegerField(default=1)
    series_max = models.PositiveSmallIntegerField(default=9)
    series_default = models.PositiveSmallIntegerField(default=1)
    reps_min = models.PositiveSmallIntegerField(default=5)
    reps_max = models.PositiveSmallIntegerField(default=30)
    reps_default = models.PositiveSmallIntegerField(default=15)

    #: Incrementa a cada save de qualquer modelo desta spec. É o número que o relatório vai
    #: carimbar (T-075) para poder dizer sob qual configuração a sessão foi produzida.
    version = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "site_config"
        verbose_name = "configuração do site"
        verbose_name_plural = "configuração do site"

    def __str__(self) -> str:
        return f"configuração v{self.version}"

    def save(self, *args, **kwargs) -> None:
        self.pk = 1
        super().save(*args, **kwargs)

    def clean(self) -> None:
        erros: dict[str, str] = {}
        if self.series_min > self.series_max:
            erros["series_min"] = "mínimo acima do máximo."
        if self.reps_min > self.reps_max:
            erros["reps_min"] = "mínimo acima do máximo."
        if not self.series_min <= self.series_default <= self.series_max:
            erros["series_default"] = "default fora da própria faixa."
        if not self.reps_min <= self.reps_default <= self.reps_max:
            erros["reps_default"] = "default fora da própria faixa."
        if self.cloud_slots > 32:
            erros["cloud_slots"] = "acima do que a VPS aguenta (4 vCPU / 6 GB)."
        if erros:
            raise ValidationError(erros)


class UserManager(BaseUserManager):
    """Criação de conta com e-mail normalizado."""

    def create_user(self, email: str, password: str, **extra) -> User:
        if not email:
            raise ValueError("e-mail obrigatorio")
        # `lower()` além do `normalize_email` (que só baixa o domínio): duas contas separadas
        # por maiúscula no local-part seriam a mesma pessoa tentando entrar e não conseguindo.
        usuario = self.model(email=self.normalize_email(email).lower(), **extra)
        usuario.password = make_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_superuser(self, email: str, password: str, **extra) -> User:
        """Conta de operador: painel + ferramentas de diagnóstico (`manage.py createsuperuser`).

        É a porta de bootstrap do painel da SPEC-018 — a primeira conta com `is_staff` tem de
        nascer de um shell na máquina, porque não há painel para criá-la ainda.

        Continua **não** sendo superusuário no sentido do Django: não há `PermissionsMixin`,
        grupos nem permissão por modelo (ver `has_perm` abaixo). E o acesso ao painel não é
        acesso ao treino de ninguém: as rotas da API continuam filtrando por dono da sessão.
        """
        extra.setdefault("is_admin", True)
        extra.setdefault("is_staff", True)
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser):
    """Conta do produto (SPEC-011, Fase Inicial): e-mail + senha, sem mais nada.

    `AbstractBaseUser` e **não** `AbstractUser`: o modelo padrão do Django traz `username`
    (obrigatório e único, enquanto a spec autentica por e-mail), `first_name`/`last_name` e a
    árvore de permissões do admin. Nada disso tem uso aqui, e cada campo herdado é uma
    migration a mais para sempre.

    Sem `PermissionsMixin` pelo mesmo motivo: não há admin nem grupos. Se um painel nascer,
    ele adiciona o mixin com uma migration — o caminho inverso (arrancar permissões de um
    modelo em produção) é que seria caro.
    """

    email = models.EmailField(unique=True, max_length=254)
    #: Como a pessoa quer ser chamada no HUD. Opcional: pedir nome no cadastro é fricção, e o
    #: funil da SPEC-011 é o produto.
    name = models.CharField(max_length=80, blank=True)
    is_active = models.BooleanField(default=True)
    #: Vê as ferramentas de diagnóstico no cliente, inclusive em produção (T-048). Chamado
    #: `is_admin` e não `is_staff` de propósito: `is_staff` é o campo que o admin do Django
    #: consulta, e não há admin aqui — reusar o nome prometeria uma semântica que o projeto
    #: não tem. Não dá acesso a dado de ninguém: as rotas continuam por dono da sessão.
    is_admin = models.BooleanField(default=False)
    #: Entra no painel de operação (SPEC-018). Campo NOVO, e não um apelido do `is_admin` acima,
    #: porque aquele foi concedido a contas existentes sob a promessa escrita de que "não dá
    #: acesso a dado de ninguém" — transformá-lo em acesso ao painel quebraria a promessa para
    #: trás, sem ninguém revisar quem já a tem. Como o `is_admin`, só é concedido por shell
    #: (`manage.py createsuperuser` ou `admin_tools --panel-on`): nenhuma rota da API o aceita.
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    #: Plano da conta (SPEC-018). Nulo é o caso normal e significa "o plano default" — e não
    #: "sem plano": atribuir `free` a toda conta existente na migration criaria milhares de FKs
    #: para dizer o que a ausência já diz, e obrigaria a um UPDATE em massa no dia em que o
    #: default mudasse de nome.
    plan = models.ForeignKey(
        "api.Plan",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="users",
    )
    #: Quando a assinatura expira. Nulo = sem prazo. Vencido cai para o default **na leitura**
    #: (`capabilities_for`), sem job de expiração: um cron que rebaixa contas seria um segundo
    #: lugar onde o plano é decidido, e o dia em que ele não rodasse ninguém notaria.
    plan_until = models.DateTimeField(null=True, blank=True)

    #: Meta diária de sessões válidas (SPEC-019). Mora no `User` e não no `Plan` porque é
    #: escolha de quem treina, não capacidade comprada — e é de graça em todo plano.
    daily_goal = models.CharField(
        max_length=12,
        choices=DailyGoal.choices,
        default=DailyGoal.CASUAL,
        verbose_name="meta diária",
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        db_table = "app_user"
        verbose_name = "conta"
        verbose_name_plural = "contas"

    def __str__(self) -> str:
        return self.email

    # Os três métodos abaixo são o contrato mínimo que o painel exige de um usuário, e são a
    # razão de `PermissionsMixin` continuar fora (SPEC-018): respondendo aqui, o `ModelBackend`
    # nunca é consultado, e `auth_user_user_permissions`/`auth_user_groups` seguem como as
    # tabelas vazias que a descoberta `[A/T-022]` registrou. Quem entra no painel enxerga tudo
    # que está registrado; granularidade por modelo entra junto com o mixin, no dia em que
    # houver mais de um perfil de operador — e não antes, porque permissão que ninguém
    # diferencia é só cerimônia.

    def has_perm(self, perm: str, obj: object | None = None) -> bool:
        return self.is_active and self.is_staff

    def has_module_perms(self, app_label: str) -> bool:
        return self.is_active and self.is_staff

    def get_all_permissions(self, obj: object | None = None) -> set[str]:
        """A mesma resposta do `has_perm`, na forma de conjunto (T-130).

        O admin do Django nunca chama isto — ele pergunta uma permissão por vez. Quem chama é o
        tema do painel (jazzmin, `utils.get_view_permissions`), em toda página, para decidir
        quais atalhos de modelo desenhar num menu. Sem o método a resposta seria `AttributeError`
        na primeira tela depois do login, e não um menu a menos.

        Devolver `set()` seria mais curto e estaria ERRADO da pior maneira: um atalho de modelo
        configurado no menu simplesmente não apareceria, sem erro nenhum para investigar —
        enquanto `has_perm` continuaria dizendo "pode" para o mesmo modelo. Duas respostas
        diferentes para a mesma pergunta é exatamente o que este método existe para não criar.

        O conjunto sai do registro de apps e **não** da tabela `auth_permission`: assim ele não
        depende de o `post_migrate` ter rodado, não custa uma consulta por página, e não pode
        divergir do `has_perm` acima.
        """
        if not (self.is_active and self.is_staff):
            return set()

        from django.apps import apps as registro_de_apps
        from django.contrib.auth import get_permission_codename

        permissoes: set[str] = set()
        for modelo in registro_de_apps.get_models():
            meta = modelo._meta
            for acao in meta.default_permissions:
                permissoes.add(f"{meta.app_label}.{get_permission_codename(acao, meta)}")
            for codename, _rotulo in meta.permissions:
                permissoes.add(f"{meta.app_label}.{codename}")
        return permissoes

    def to_dict(self) -> dict[str, object]:
        """Corpo do `GET /api/me` e do bloco `user` das respostas de auth."""
        return {
            "id": self.pk,
            "email": self.email,
            "name": self.name,
            "is_admin": self.is_admin,
            "daily_goal": self.daily_goal,
            "date_joined": self.date_joined.isoformat(),
        }


class SessionClaim(models.Model):
    """De quem é a sessão, registrado na admissão (SPEC-011).

    `user` nulo é o caso normal e não é exceção: a Fase 0 inteira é anônima e o trial existe
    para que continue sendo — a conta é o degrau seguinte do funil, não o pedágio da entrada.

    `device_id` é o que o trial conta (3 sessões/dia). Fica aqui, e não só no contador do
    Redis, porque o contador expira e a pergunta "quantas sessões este aparelho já fez?"
    sobrevive a ele.
    """

    session_id = models.CharField(max_length=64, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    device_id = models.CharField(max_length=64, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "session_claim"
        ordering = ["-created_at"]
        verbose_name = "dono de sessão"
        verbose_name_plural = "donos de sessão"

    def __str__(self) -> str:
        return f"{self.session_id} · {self.user or 'anonimo'}"


class SessionResult(models.Model):
    """Relatório consolidado de uma sessão de 30 s.

    `session_id` é único e é a chave de negócio: o report-builder faz upsert por ele. Isso é o
    que permite reprocessar o mesmo `session.completed` — depois de um crash, ou num replay do
    stream — sem criar duas linhas para a mesma sessão (SPEC-010, critério 2).

    `CharField` e não `UUIDField`: o id vem do envelope, e nem todo produtor de eventos é a
    API. A bancada de avaliação (SPEC-012) usa ids legíveis como `polichinelo-01`, e um campo
    UUID recusaria persistir justamente as sessões que servem para medir o sistema.
    """

    session_id = models.CharField(max_length=64, unique=True)
    exercise = models.CharField(max_length=40)
    mode = models.CharField(max_length=16)
    #: `SessionEndReason` do contrato. Guardado como texto: o motivo é dado do relatório, e um
    #: enum do banco obrigaria migration a cada motivo novo.
    reason = models.CharField(max_length=16)

    rep_count = models.PositiveIntegerField(default=0)
    #: Duração **efetiva**: da calibração ao fim. Não é o tempo de conexão.
    duration_ms = models.PositiveIntegerField(default=0)
    cadence_rpm = models.FloatField(default=0.0)

    cadence_windows = models.JSONField(default=list)
    rep_durations_ms = models.JSONField(default=list)
    feedback_counts = models.JSONField(default=dict)
    scene_warning_counts = models.JSONField(default=dict)
    calibration_samples = models.PositiveIntegerField(default=0)
    #: Versão da configuração (`SiteConfig.version`) que valia quando esta sessão foi admitida
    #: (SPEC-018, critério 8). Chega carimbada no `session.started` e nunca é consultada aqui:
    #: o relatório é derivável por replay, e ler a configuração no momento da gravação diria a
    #: versão de HOJE sobre uma sessão de ontem.
    #:
    #: `0` é "não registrada": sessão anterior a esta coluna, ou admitida com a configuração
    #: fora do ar (P2, valores do código). Os dois casos compartilham o valor de propósito —
    #: nos dois, a resposta honesta é a mesma.
    config_version = models.PositiveIntegerField(default=0)

    #: Carimbos de série da SPEC-023 (T-134): como a série terminou (`livre`/`contado`) e onde
    #: ela mora dentro do treino. `set_mode` e não `mode` de propósito — `mode` acima já é o
    #: modo de extração de pose (edge/cloud), eixo diferente da mesma sessão.
    set_mode = models.CharField(max_length=16, default="livre")
    target_reps = models.PositiveIntegerField(default=0)
    set_index = models.PositiveSmallIntegerField(default=0)
    set_total = models.PositiveSmallIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "session_result"
        ordering = ["-created_at"]
        verbose_name = "treino realizado"
        verbose_name_plural = "treinos realizados"

    def __str__(self) -> str:
        return f"{self.session_id} · {self.exercise} · {self.rep_count} reps"

    def to_report(self) -> dict[str, object]:
        """Corpo do `GET /api/sessions/{id}/report`.

        Campos em snake_case, iguais aos do contrato de eventos: o cliente já lê o fio nesse
        formato, e traduzir aqui criaria uma segunda convenção para os mesmos dados.
        """
        return {
            "session_id": self.session_id,
            "exercise": self.exercise,
            "mode": self.mode,
            "reason": self.reason,
            "rep_count": self.rep_count,
            "duration_ms": self.duration_ms,
            "cadence_rpm": self.cadence_rpm,
            "cadence_windows": self.cadence_windows,
            "rep_durations_ms": self.rep_durations_ms,
            "feedback_counts": self.feedback_counts,
            "scene_warning_counts": self.scene_warning_counts,
            "calibration_samples": self.calibration_samples,
            "config_version": self.config_version,
            "set_mode": self.set_mode,
            "target_reps": self.target_reps,
            "set_index": self.set_index,
            "set_total": self.set_total,
            "created_at": self.created_at.isoformat(),
        }
