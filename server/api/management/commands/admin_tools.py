"""Liga e desliga os dois acessos privilegiados de uma conta (T-048, T-072).

    python manage.py admin_tools daniel@exemplo.com          # mostra o estado dos dois
    python manage.py admin_tools daniel@exemplo.com --on     # ferramentas de diagnóstico
    python manage.py admin_tools daniel@exemplo.com --off
    python manage.py admin_tools daniel@exemplo.com --panel-on    # painel de operação
    python manage.py admin_tools daniel@exemplo.com --panel-off
    python manage.py admin_tools --list

Existe porque nenhuma das duas flags é aceita no cadastro nem em rota nenhuma da API: se
fossem, bastaria um `is_admin: true` no corpo do `POST /api/auth/register` para qualquer
visitante se promover. A única porta é esta, e ela exige shell na máquina — em produção,
`./scripts/prod.sh exec api python manage.py admin_tools <email> --panel-on`.

**São dois acessos diferentes, de propósito** (SPEC-018):

- `is_admin` (`--on`) concede a superfície de dev do CLIENTE: chip de diagnóstico, gravador de
  fixtures, fonte de vídeo da T-040. Não abre dado de ninguém — histórico e relatório continuam
  filtrados por dono da sessão, como na SPEC-011.
- `is_staff` (`--panel-on`) concede o PAINEL, que lê contas e sessões de todo mundo. Nasceu
  separado justamente para que as contas concedidas sob a promessa acima não virassem acesso ao
  painel por efeito colateral de uma migration.

A primeira conta de operador não sai daqui e sim de `manage.py createsuperuser`, que já cria com
as duas ligadas: sem painel ainda não há painel para conceder painel.
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError

from api.models import User


class Command(BaseCommand):
    help = "Liga/desliga as ferramentas de diagnóstico e o painel de uma conta."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("email", nargs="?", help="e-mail da conta")
        # Um grupo por acesso: `--on --panel-on` numa chamada só é o caso normal de promover
        # alguém, e obrigar a rodar o comando duas vezes seria cerimônia sem propriedade.
        ferramentas = parser.add_mutually_exclusive_group()
        ferramentas.add_argument("--on", action="store_true", help="concede as ferramentas")
        ferramentas.add_argument("--off", action="store_true", help="revoga as ferramentas")
        painel = parser.add_mutually_exclusive_group()
        painel.add_argument("--panel-on", action="store_true", help="concede o painel")
        painel.add_argument("--panel-off", action="store_true", help="revoga o painel")
        parser.add_argument("--list", action="store_true", help="lista quem tem acesso hoje")

    def handle(self, *args: Any, **options: Any) -> None:
        if options["list"]:
            self._listar()
            return

        email = options["email"]
        if not email:
            raise CommandError("informe o e-mail da conta (ou use --list)")

        # Mesma normalização do cadastro: quem digita com maiúscula acha a própria conta.
        try:
            usuario = User.objects.get(email=email.strip().lower())
        except User.DoesNotExist:
            raise CommandError(f"nao existe conta com o e-mail {email}") from None

        mudou: list[str] = []
        if options["on"] or options["off"]:
            usuario.is_admin = bool(options["on"])
            mudou.append("is_admin")
        if options["panel_on"] or options["panel_off"]:
            usuario.is_staff = bool(options["panel_on"])
            mudou.append("is_staff")

        if not mudou:
            self.stdout.write(self._estado(usuario))
            return

        usuario.save(update_fields=mudou)
        # O cliente lê `is_admin` no `GET /api/me`, que roda na abertura do app: a mudança
        # aparece no próximo carregamento da página, sem precisar sair e entrar. Já o painel
        # é decidido a cada requisição, então revogar derruba o acesso na hora.
        self.stdout.write(self.style.SUCCESS(self._estado(usuario)))

    def _estado(self, usuario: User) -> str:
        ferramentas = "ligadas" if usuario.is_admin else "desligadas"
        painel = "liberado" if usuario.is_staff else "bloqueado"
        return f"{usuario.email}: ferramentas {ferramentas}, painel {painel}"

    def _listar(self) -> None:
        from django.db.models import Q

        contas = User.objects.filter(Q(is_admin=True) | Q(is_staff=True)).order_by("email")
        if not contas:
            self.stdout.write("nenhuma conta com acesso privilegiado")
            return
        for usuario in contas:
            self.stdout.write(self._estado(usuario))
