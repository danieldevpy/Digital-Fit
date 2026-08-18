"""Buraco de tradução no banco — visível, nunca silencioso (SPEC-025, T-146).

    python manage.py i18n_status                 # só o que está habilitado (o que vai ao ar)
    python manage.py i18n_status --todos          # inventário completo, inclusive desligado
    python manage.py i18n_status --json           # para CI ou para colar no DEVLOG

Comando e não tela, como o `exercise_health` (T-104): é leitura de operador, roda no mesmo
processo que já tem ORM. A conta está em `api/i18n_status.py` — o painel (`admin.py`) e este
comando concordam porque leem o mesmo `Exercise.translations`/`Plan.translations`, nunca dois
cálculos separados do que "está traduzido".
"""

from __future__ import annotations

import json
from typing import Any

from django.core.management.base import BaseCommand

from api.i18n_status import Relatorio, coletar


class Command(BaseCommand):
    help = "Exercicios e planos com texto em pt-BR sem traducao correspondente (SPEC-025)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--todos",
            action="store_true",
            help="inclui exercicio desligado (fora do catalogo servido, mas ainda no banco)",
        )
        parser.add_argument(
            "--json", action="store_true", help="saida em JSON, sem legenda nem cor"
        )

    def handle(self, *args: Any, **options: Any) -> None:
        relatorio = coletar(apenas_habilitados=not options["todos"])

        if options["json"]:
            self.stdout.write(json.dumps(relatorio.to_dict(), indent=2, ensure_ascii=False))
            return

        if relatorio.ok:
            self.stdout.write(
                self.style.SUCCESS("nada para traduzir — todo texto tem par em todo idioma")
            )
            return

        self.stdout.write(
            self.style.WARNING(f"{relatorio.total} buraco(s) de traducao encontrado(s)\n")
        )
        for gap in relatorio.exercicios:
            self.stdout.write(self._linha_exercicio(gap, relatorio))
        for gap in relatorio.planos:
            self.stdout.write(self._linha_plano(gap))

    def _linha_exercicio(self, gap: Any, relatorio: Relatorio) -> str:
        partes = []
        if gap.campos_faltando:
            partes.append(", ".join(gap.campos_faltando))
        if gap.passos_faltando:
            plural = "passo" if gap.passos_faltando == 1 else "passos"
            partes.append(f"{gap.passos_faltando} {plural} do guia")
        detalhe = "; ".join(partes)
        return self.style.ERROR(
            f"exercicio  {gap.slug:<20} [{gap.locale}]  falta: {detalhe}"
        )

    def _linha_plano(self, gap: Any) -> str:
        detalhe = ", ".join(gap.campos_faltando)
        return self.style.ERROR(f"plano      {gap.slug:<20} [{gap.locale}]  falta: {detalhe}")
