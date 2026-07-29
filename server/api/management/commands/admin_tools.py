"""Liga e desliga o acesso às ferramentas de diagnóstico de uma conta (T-048).

    python manage.py admin_tools daniel@exemplo.com          # mostra o estado
    python manage.py admin_tools daniel@exemplo.com --on
    python manage.py admin_tools daniel@exemplo.com --off
    python manage.py admin_tools --list

Existe porque `is_admin` **não** é aceito no cadastro nem em nenhuma rota da API: se fosse,
bastaria um `is_admin: true` no corpo do `POST /api/auth/register` para qualquer visitante se
promover. A única porta é esta, e ela exige shell na máquina — em produção,
`./scripts/prod.sh exec api python manage.py admin_tools <email> --on`.

O que a flag concede é a superfície de dev do cliente (chip de diagnóstico, gravador de
fixtures, e a fonte de vídeo da T-040). Não concede acesso a dado de ninguém: histórico e
relatório continuam filtrados por dono da sessão, como na SPEC-011.
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError

from api.models import User


class Command(BaseCommand):
    help = "Liga/desliga as ferramentas de diagnóstico de uma conta."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("email", nargs="?", help="e-mail da conta")
        grupo = parser.add_mutually_exclusive_group()
        grupo.add_argument("--on", action="store_true", help="concede o acesso")
        grupo.add_argument("--off", action="store_true", help="revoga o acesso")
        parser.add_argument("--list", action="store_true", help="lista quem tem o acesso hoje")

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

        if not options["on"] and not options["off"]:
            estado = "ligadas" if usuario.is_admin else "desligadas"
            self.stdout.write(f"{usuario.email}: ferramentas {estado}")
            return

        usuario.is_admin = bool(options["on"])
        usuario.save(update_fields=["is_admin"])
        acao = "ligadas" if usuario.is_admin else "desligadas"
        self.stdout.write(
            self.style.SUCCESS(f"{usuario.email}: ferramentas {acao}")
            # O cliente lê a flag no `GET /api/me`, que roda na abertura do app: a mudança
            # aparece no próximo carregamento da página, sem precisar sair e entrar.
        )

    def _listar(self) -> None:
        contas = User.objects.filter(is_admin=True).order_by("email")
        if not contas:
            self.stdout.write("nenhuma conta com ferramentas de diagnostico")
            return
        for usuario in contas:
            self.stdout.write(usuario.email)
