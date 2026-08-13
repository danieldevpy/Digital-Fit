"""Saúde de cada exercício em produção (T-104 / SPEC-020).

    python manage.py exercise_health              # últimos 7 dias
    python manage.py exercise_health --dias 30
    python manage.py exercise_health --json       # para colar no DEVLOG

Comando e não tela, como a SPEC-020 pede: é leitura de operador, roda no mesmo processo que já
tem ORM, e não custa superfície de painel. O painel mostra só o que precisa de ação — um
exercício acima do limite entra na faixa de avisos do dashboard (T-130).

A conta está em `api/exercise_health.py`, e o motivo de estar lá é que o painel lê os MESMOS
números: dois lugares calculando "taxa de zero-rep" acabariam discordando, e o dia em que
discordassem ninguém saberia qual acreditar.
"""

from __future__ import annotations

import json
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from api.exercise_health import (
    JANELA_PADRAO_DIAS,
    LIMITE_ZERO,
    MINIMO_PARA_VEREDITO,
    ExerciseHealth,
    coletar,
)

#: Largura das colunas. Fixa, porque a saída é lida por gente num terminal — e uma tabela que
#: muda de forma conforme o dado é mais difícil de comparar entre dois dias.
_CABECALHO = (
    f"{'exercicio':<24}{'maturidade':<14}{'sessoes':>8}{'completas':>11}"
    f"{'zeradas':>9}{'taxa':>8}{'sem dado':>11}{'cadencia':>11}  veredito"
)

_VEREDITOS = {
    "ok": ("ok", "SUCCESS"),
    "atencao": ("ATENCAO", "ERROR"),
    "poucas": (f"poucas (<{MINIMO_PARA_VEREDITO})", "WARNING"),
    "sem sessao": ("sem sessao", "NOTICE"),
}


class Command(BaseCommand):
    help = "Taxa de sessoes zero-rep, total e cadencia mediana por exercicio (SPEC-020)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--dias",
            type=int,
            default=JANELA_PADRAO_DIAS,
            help=f"janela em dias (padrao {JANELA_PADRAO_DIAS}, a da SPEC-020)",
        )
        parser.add_argument(
            "--json", action="store_true", help="saida em JSON, sem tabela nem legenda"
        )

    def handle(self, *args: Any, **options: Any) -> None:
        dias = options["dias"]
        if dias < 1:
            raise CommandError("--dias tem de ser >= 1")

        saude = coletar(dias)

        if options["json"]:
            corpo = {
                "dias": dias,
                "limite_zero": LIMITE_ZERO,
                "exercicios": [linha.to_dict() for linha in saude],
            }
            self.stdout.write(json.dumps(corpo, indent=2, ensure_ascii=False))
            return

        if not saude:
            self.stdout.write("nenhum exercicio no catalogo e nenhuma sessao gravada")
            return

        self.stdout.write(f"saude dos exercicios · ultimos {dias} dia(s)\n")
        self.stdout.write(_CABECALHO)
        self.stdout.write("-" * len(_CABECALHO))
        for exercicio in saude:
            self.stdout.write(self._linha(exercicio))
        self.stdout.write("")
        for aviso in _legenda(saude):
            self.stdout.write(aviso)

    def _linha(self, e: ExerciseHealth) -> str:
        texto, estilo = _VEREDITOS[e.veredito]
        # Exercício fora do ar continua na tabela: foi desligado JUSTAMENTE porque alguém viu
        # um número aqui, e sumir com a linha apagaria a prova. O corte vem ANTES do marcador
        # — cortar depois transformaria "(off)" em "(of" no primeiro nome comprido.
        nome = e.display_name[:17] + ("" if e.enabled else " (off)")
        maturidade = e.maturity or "fora do cat."
        corpo = (
            f"{nome:<24}{maturidade:<14}{e.total:>8}"
            f"{_ou_traco(e.completas, e.total):>11}"
            f"{_ou_traco(e.zeradas, e.completas):>9}"
            f"{_percentual(e.taxa_zero):>8}"
            f"{_sem_dado(e):>11}"
            f"{_cadencia(e.cadencia_mediana):>11}  "
        )
        return corpo + getattr(self.style, estilo)(texto)


def _ou_traco(valor: int, denominador: int) -> str:
    """`--` quando não há do que o número ser parte. Zero e "não se aplica" são coisas
    diferentes, e imprimir `0` nos dois casos esconde a segunda."""
    return "--" if denominador == 0 else str(valor)


def _percentual(taxa: float | None) -> str:
    return "--" if taxa is None else f"{taxa * 100:.1f}%"


def _sem_dado(e: ExerciseHealth) -> str:
    taxa = e.taxa_sem_dado
    return "--" if taxa is None else f"{e.sem_dado} ({taxa * 100:.0f}%)"


def _cadencia(mediana: float | None) -> str:
    return "--" if mediana is None else f"{mediana:.1f} rpm"


def _legenda(saude: list[ExerciseHealth]) -> list[str]:
    """O que a tabela quer dizer, e o que fazer com ela.

    A legenda existe porque as duas colunas de zero são fáceis de confundir — e confundi-las
    já custou semanas (T-133). Quem abre este comando pela primeira vez precisa sair sabendo
    que elas têm donos diferentes.
    """
    linhas = [
        f"taxa = zeradas / completas. A SPEC-020 exige < {LIMITE_ZERO * 100:.0f}% para `validado`.",
        "'sem dado' sao sessoes `no_data` (10 s sem frame): captura, nao contagem — ficam "
        "FORA da taxa.",
    ]
    atencao = [e for e in saude if e.veredito == "atencao"]
    if atencao:
        nomes = ", ".join(e.display_name for e in atencao)
        linhas.append(f"acima do limite: {nomes}. Rebaixar a maturidade tira do Free sem deploy.")
    altos = [e for e in saude if (e.taxa_sem_dado or 0) >= 0.5 and e.total >= MINIMO_PARA_VEREDITO]
    if altos:
        nomes = ", ".join(e.display_name for e in altos)
        linhas.append(
            f"mais da metade das sessoes sem frame: {nomes}. Isto nao e a FSM — e camera, "
            "aba fechada ou rede."
        )
    return linhas
