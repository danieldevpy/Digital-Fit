"""Exporta o catálogo público para o build do site (SPEC-026 §Escopo, T-165).

    python manage.py export_site_catalog                 # escreve web/src/site/exercicios.json
    python manage.py export_site_catalog --out -         # imprime, para conferir sem gravar
    python manage.py export_site_catalog --check         # falha se o arquivo estiver desatualizado

O passo que liga o Postgres ao pré-render sem pôr banco dentro do build — ver o cabeçalho de
`api/site_catalog.py` para o porquê. Roda no `scripts/prod.sh`, antes do `compose build`.

O `--check` existe para o CI: ele não escreve nada e devolve código 1 quando o arquivo
versionado não bate com o banco. É o que impede um exercício novo de ficar meses sem página
porque alguém esqueceu de reexportar — o mesmo papel que o `i18n_status` tem para tradução.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from api.site_catalog import SlugDuplicado, catalogo_publico

#: O destino padrão, relativo à raiz do repositório. Dentro de `src/` e não de `public/` porque
#: ele é **entrada do build** (o roteador e o pré-render o consomem em tempo de compilação),
#: não arquivo servido: nada aqui precisa chegar ao navegador em runtime.
DESTINO_PADRAO = Path("web/src/site/exercicios.json")


def _raiz_do_repo() -> Path:
    # .../server/api/management/commands/export_site_catalog.py -> .../
    return Path(__file__).resolve().parents[4]


def _serializar(dados: dict[str, Any]) -> str:
    # `indent=2` e `ensure_ascii=False`: o arquivo é versionado e revisado por gente, então o
    # diff precisa ser legível e "agachamento" precisa aparecer como "agachamento". Quebra de
    # linha no fim para o arquivo terminar como todo arquivo de texto do repositório.
    return json.dumps(dados, indent=2, ensure_ascii=False, sort_keys=False) + "\n"


class Command(BaseCommand):
    help = "Escreve o catalogo publico (paginas por exercicio) para o build do site."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--out",
            default=None,
            help=f"destino ('-' imprime na saida padrao). Default: {DESTINO_PADRAO}",
        )
        parser.add_argument(
            "--check",
            action="store_true",
            help="nao escreve; sai com 1 se o arquivo versionado estiver desatualizado",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            dados = catalogo_publico()
        except SlugDuplicado as erro:
            raise CommandError(str(erro)) from erro

        texto = _serializar(dados)
        quantos = len(dados["exercicios"])

        if options["out"] == "-":
            self.stdout.write(texto)
            return

        destino = Path(options["out"]) if options["out"] else _raiz_do_repo() / DESTINO_PADRAO

        if options["check"]:
            atual = destino.read_text(encoding="utf-8") if destino.exists() else ""
            if atual != texto:
                raise CommandError(
                    f"{destino} esta desatualizado em relacao ao banco. "
                    f"Rode `manage.py export_site_catalog` e versione o resultado."
                )
            self.stdout.write(self.style.SUCCESS(f"{destino} em dia ({quantos} exercicios)"))
            return

        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"{quantos} exercicios -> {destino}"))
