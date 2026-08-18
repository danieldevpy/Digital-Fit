"""Texto do servidor em arquivo — conquistas e `detail` de erro do cliente (SPEC-025, T-145).

Duas fontes de texto do servidor viviam no código antes desta task: o nome/descrição de cada
`Conquista` (`api/engagement.py`) e o `detail` dos erros 4xx voltados ao cliente em `api/auth.py`
e `api/sessions.py`. As duas saem para `messages.<locale>.yaml`, ao lado deste módulo — mesmo
padrão do `FeedbackCatalog` (`workers/analysis_worker/feedback`, T-144): YAML carregado em
código, um arquivo por idioma, nunca `.po`/`.mo`.

**Por que um módulo à parte, e não dentro de `api/i18n/__init__.py`.** Aquele pacote resolve
*qual* locale vale para a requisição (`resolve_locale`); este resolve *o texto* desse locale. A
mesma fronteira que já separa `resolve_locale` do catálogo de feedback (ver o docstring do
pacote) separa este catálogo dele.

**Fallback por CHAVE, não por arquivo.** O `FeedbackCatalog` cai no arquivo `pt-BR` inteiro
quando o locale pedido não tem arquivo próprio — aqui o fallback é mais fino: cada `achievement`/
`error` ausente no locale pedido cai na entrada correspondente de `SOURCE_LOCALE`, sem derrubar
as chaves que aquele locale já tem. `pytest` cobra paridade total entre os dois YAML
(`tests/test_i18n_messages.py`), então na prática os dois sempre têm o mesmo conjunto de chaves
— o fallback por chave é a rede de segurança para um deploy no meio de uma tradução em
andamento, não uma saída planejada.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from api.i18n import SOURCE_LOCALE

__all__ = ["MESSAGES_DIR", "Messages", "load"]

MESSAGES_DIR = Path(__file__).resolve().parent


def _path_for(locale: str) -> Path:
    """`messages.<locale>.yaml`, ou o de `SOURCE_LOCALE` se o idioma não tem arquivo próprio."""
    candidato = MESSAGES_DIR / f"messages.{locale}.yaml"
    return candidato if candidato.exists() else MESSAGES_DIR / f"messages.{SOURCE_LOCALE}.yaml"


@dataclass(frozen=True, slots=True)
class Messages:
    """Conquistas e mensagens de erro de um locale, já carregadas."""

    achievements: dict[str, dict[str, str]]
    errors: dict[str, str]

    @classmethod
    def _read(cls, path: Path) -> Messages:
        import yaml

        bruto: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return cls(
            achievements={
                str(slug): {str(campo): str(valor) for campo, valor in (entrada or {}).items()}
                for slug, entrada in (bruto.get("achievements") or {}).items()
            },
            errors={str(chave): str(valor) for chave, valor in (bruto.get("errors") or {}).items()},
        )

    def achievement(self, slug: str) -> dict[str, str]:
        """`{"name": ..., "description": ...}` da conquista, com fallback por chave."""
        entrada = self.achievements.get(slug)
        if entrada:
            return entrada
        return load(SOURCE_LOCALE).achievements.get(slug, {})

    def error(self, key: str, **valores: Any) -> str:
        """O `detail` de `key` neste locale, interpolado por `str.format`.

        `key` sem entrada em nenhum dos dois lados devolve a própria chave — locale é
        preferência de exibição, e um `KeyError` no meio da montagem de um erro seria pior que um
        texto feio na tela.
        """
        texto = self.errors.get(key)
        if texto is None:
            texto = load(SOURCE_LOCALE).errors.get(key, key)
        return texto.format(**valores) if valores else texto


@lru_cache(maxsize=8)
def load(locale: str = SOURCE_LOCALE) -> Messages:
    """`messages.<locale>.yaml` (ou o de `SOURCE_LOCALE`, ver `_path_for`), do cache.

    `lru_cache` por locale — mesmo padrão do `_mensagens_de_feedback` em `api/config.py`
    (SPEC-025 §Notas técnicas): o arquivo é do deploy, não do banco, então mudou o YAML, mudou o
    processo; o que este cache evita é reabrir e reanalisar o mesmo arquivo a cada requisição.
    """
    return Messages._read(_path_for(locale))
