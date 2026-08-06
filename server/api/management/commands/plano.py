"""Atribui, mostra e revoga o plano de uma conta (SPEC-016 / SPEC-018 §E).

    python manage.py plano ana@exemplo.com                      # mostra o plano de hoje
    python manage.py plano ana@exemplo.com --set subscriber     # 365 dias, o default
    python manage.py plano ana@exemplo.com --set subscriber --dias 30
    python manage.py plano ana@exemplo.com --set subscriber --sem-prazo
    python manage.py plano ana@exemplo.com --clear              # volta ao plano default
    python manage.py plano --list                               # planos que existem

Enquanto o checkout não existe (T-036), **é assim que alguém vira assinante**: à mão, com
shell na máquina. A SPEC-018 §E já previa este caminho — atribuir plano é operação de
suporte, não configuração —, e a única razão de ele ter nascido como script solto é que ele
foi escrito com pressa, num dia em que o assinante precisava existir.

Ser um comando de manage e não um `.sh` com Python dentro de um heredoc paga três coisas que
o script não tinha como pagar:

1. **O ORM valida.** Plano inexistente vira erro com a lista do que existe, e não um
   `Plan.DoesNotExist` cru no meio da saída do shell.
2. **Dá para testar.** `call_command` roda isto sem docker, sem VPS e sem banco de produção —
   e é o que impede o próximo conserto de quebrar em silêncio.
3. **Roda igual em qualquer lugar.** Local, container de dev ou produção: quem escolhe o
   ambiente é o `manage.py`, não uma linha de `docker compose exec` embutida no arquivo.

O prazo é o `plan_until` que já existe. Quem rebaixa a conta vencida é a **leitura**
(`capabilities_for`), não um cron: um job que rebaixasse contas seria um segundo lugar onde o
plano é decidido, e o dia em que ele não rodasse ninguém notaria.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from api.models import Plan, User

#: Um ano. O plano pago é anual no discurso do produto, e um prazo é melhor que `null` mesmo
#: para conta de teste: assinatura sem data de fim é a que ninguém lembra de revisar.
DIAS_PADRAO = 365


class Command(BaseCommand):
    help = "Mostra, atribui ou revoga o plano de uma conta."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("email", nargs="?", help="e-mail da conta")
        alvo = parser.add_mutually_exclusive_group()
        alvo.add_argument("--set", dest="slug", help="slug do plano (ex.: subscriber)")
        alvo.add_argument(
            "--clear",
            action="store_true",
            help="remove o plano e o prazo — a conta volta ao default",
        )
        parser.add_argument(
            "--dias", type=int, default=DIAS_PADRAO, help=f"prazo em dias (padrão {DIAS_PADRAO})"
        )
        parser.add_argument(
            "--sem-prazo",
            dest="sem_prazo",
            action="store_true",
            help="atribui sem data de fim (`plan_until` nulo)",
        )
        parser.add_argument("--list", action="store_true", help="lista os planos que existem")

    def handle(self, *args: Any, **options: Any) -> None:
        if options["list"]:
            self._listar_planos()
            return

        email = options["email"]
        if not email:
            raise CommandError("informe o e-mail da conta (ou use --list)")

        # Mesma normalização do cadastro, igual ao `admin_tools`: quem digita com maiúscula
        # acha a própria conta em vez de ouvir que ela não existe.
        try:
            usuario = User.objects.get(email=email.strip().lower())
        except User.DoesNotExist:
            raise CommandError(f"nao existe conta com o e-mail {email}") from None

        if options["clear"]:
            usuario.plan = None
            usuario.plan_until = None
            usuario.save(update_fields=["plan", "plan_until"])
            self.stdout.write(self.style.SUCCESS(self._estado(usuario)))
            return

        slug = options["slug"]
        if not slug:
            self.stdout.write(self._estado(usuario))
            return

        try:
            plano = Plan.objects.get(slug=slug)
        except Plan.DoesNotExist:
            existentes = ", ".join(Plan.objects.order_by("ordem").values_list("slug", flat=True))
            raise CommandError(
                f"nao existe plano com o slug {slug!r}. Existem: {existentes or '(nenhum)'}"
            ) from None

        if options["dias"] < 1 and not options["sem_prazo"]:
            raise CommandError("--dias tem de ser >= 1 (ou use --sem-prazo)")

        usuario.plan = plano
        usuario.plan_until = (
            None if options["sem_prazo"] else datetime.now(UTC) + timedelta(days=options["dias"])
        )
        usuario.save(update_fields=["plan", "plan_until"])
        self.stdout.write(self.style.SUCCESS(self._estado(usuario)))

    def _estado(self, usuario: User) -> str:
        """Uma linha que responde o que quem rodou o comando foi conferir."""
        if usuario.plan is None:
            return f"{usuario.email}: plano default (sem atribuicao)"

        limite = usuario.plan.daily_sessions
        sessoes = "ilimitadas" if limite == 0 else f"{limite}/dia"
        if usuario.plan_until is None:
            prazo = "sem prazo"
        else:
            # Vencido é dito com todas as letras: `capabilities_for` já trata esta conta como
            # default, e uma linha que só mostrasse a data deixaria quem lê achando o
            # contrário — que a atribuição ainda vale.
            vencido = usuario.plan_until <= datetime.now(UTC)
            quando = usuario.plan_until.strftime("%d/%m/%Y")
            prazo = f"VENCIDO em {quando}" if vencido else f"ate {quando}"
        return f"{usuario.email}: {usuario.plan.nome} ({usuario.plan.slug}), {prazo}, {sessoes}"

    def _listar_planos(self) -> None:
        planos = Plan.objects.order_by("ordem", "slug")
        if not planos:
            self.stdout.write("nenhum plano cadastrado")
            return
        for plano in planos:
            limite = plano.daily_sessions
            sessoes = "ilimitadas" if limite == 0 else f"{limite}/dia"
            default = " (default)" if plano.is_default else ""
            self.stdout.write(f"{plano.slug:12s} {plano.nome}{default} — {sessoes}")
