"""Feedback engine — sinais crus viram feedback humano, priorizado e não-irritante (SPEC-008).

Entra `quality.signal` (execução, da FSM) e `scene.warning` (cena); sai `feedback.issued`, que é
o que o HUD mostra. Entre um e outro há três regras, e todas existem para o app não virar um
alarme:

1. **Catálogo** (`catalog.pt-BR.yaml`): código → mensagem, dica, severidade e prioridade. Texto
   fora do código, um arquivo por idioma.
2. **Prioridade**: cena antes de execução — não faz sentido criticar a amplitude do braço de
   quem está fora do quadro. E **no máximo um feedback por vez** no HUD.
3. **Throttle por código**: o mesmo código sai 1×/4 s no máximo. Rep preguiçosa repetida gera
   feedback a cada ~4 s, nunca a cada repetição.

Motor puro: sem I/O além da leitura do catálogo. A exibição é do cliente (T-012, Agente B).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from workers.shared.events import Code, FeedbackIssued, SceneWarning, Severity

__all__ = [
    "DEFAULT_CATALOG_PATH",
    "SCENE_SUPPRESS_MS",
    "THROTTLE_MS",
    "CatalogEntry",
    "FeedbackCatalog",
    "FeedbackEngine",
]

#: Mesmo código no máximo 1×/4 s (SPEC-008, Fase Inicial).
THROTTLE_MS = 4_000

#: Enquanto um problema de cena está ativo, crítica de execução fica calada. A janela cobre o
#: intervalo de repetição do aviso de cena (2 s da SPEC-003) com folga.
SCENE_SUPPRESS_MS = 3_000

DEFAULT_CATALOG_PATH = Path(__file__).resolve().parent / "catalog.pt-BR.yaml"

#: Códigos que descrevem a **cena**, não a execução — os que suprimem os outros.
SCENE_CODES: frozenset[Code] = frozenset({Code.OUT_OF_FRAME, Code.TOO_FAR, Code.TOO_CLOSE})


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    """Uma entrada do catálogo."""

    code: Code
    message: str
    hint: str | None = None
    severity: Severity = Severity.INFO
    priority: int = 100


@dataclass(frozen=True, slots=True)
class FeedbackCatalog:
    """Mensagens por código, carregadas de YAML."""

    entries: dict[Code, CatalogEntry]

    @classmethod
    def load(cls, path: Path | None = None) -> FeedbackCatalog:
        """Lê o catálogo. Código desconhecido no arquivo é erro — não silencia typo."""
        import yaml

        caminho = Path(path) if path else DEFAULT_CATALOG_PATH
        bruto: dict[str, Any] = yaml.safe_load(caminho.read_text(encoding="utf-8")) or {}
        entries: dict[Code, CatalogEntry] = {}
        for chave, valor in bruto.items():
            try:
                code = Code(chave)
            except ValueError:
                raise ValueError(
                    f"codigo desconhecido no catalogo {caminho.name}: {chave!r}"
                ) from None
            if not isinstance(valor, dict) or not valor.get("message"):
                raise ValueError(f"entrada sem `message` no catalogo: {chave!r}")
            entries[code] = CatalogEntry(
                code=code,
                message=str(valor["message"]),
                hint=str(valor["hint"]) if valor.get("hint") else None,
                severity=Severity(valor.get("severity", Severity.INFO.value)),
                priority=int(valor.get("priority", 100)),
            )
        return cls(entries=entries)

    def get(self, code: Code) -> CatalogEntry | None:
        return self.entries.get(code)

    def missing(self) -> set[Code]:
        """Códigos do contrato sem mensagem — o teste usa isso para não deixar buraco."""
        return set(Code) - set(self.entries)


@dataclass(slots=True)
class FeedbackEngine:
    """Um motor por sessão: throttle e supressão são estado."""

    catalog: FeedbackCatalog = field(default_factory=FeedbackCatalog.load)
    throttle_ms: int = THROTTLE_MS
    scene_suppress_ms: int = SCENE_SUPPRESS_MS
    counts: dict[str, int] = field(default_factory=dict)
    _last_issued: dict[Code, int] = field(default_factory=dict)
    _scene_until_ms: int | None = None

    def push(self, signals: list[Any], ts: int) -> list[FeedbackIssued]:
        """Recebe os sinais deste frame e devolve **no máximo um** feedback.

        `signals` são os payloads que a FSM e o validador de cena acabaram de produzir
        (`QualitySignal` e `SceneWarning`); qualquer outro tipo é ignorado.
        """
        candidatos = [
            (entrada, sinal) for sinal in signals if (entrada := self._entry_for(sinal)) is not None
        ]
        if not candidatos:
            return []

        # Cena ativa cala a execução (critério 2 da SPEC-008).
        if any(entrada.code in SCENE_CODES for entrada, _ in candidatos):
            self._scene_until_ms = ts + self.scene_suppress_ms
        elif self._scene_until_ms is not None and ts < self._scene_until_ms:
            return []

        candidatos.sort(key=lambda par: (par[0].priority, par[0].code.value))
        for entrada, sinal in candidatos:
            if self._throttled(entrada.code, ts):
                continue
            self._last_issued[entrada.code] = ts
            self.counts[entrada.code.value] = self.counts.get(entrada.code.value, 0) + 1
            return [
                FeedbackIssued(
                    code=entrada.code,
                    severity=self._severity(entrada, sinal),
                    message=entrada.message,
                    hint=entrada.hint,
                )
            ]
        return []

    def _entry_for(self, sinal: Any) -> CatalogEntry | None:
        code = getattr(sinal, "code", None)
        if not isinstance(code, Code):
            return None  # rep.detected e afins: insumo da Fase Evolução, não vira feedback aqui
        return self.catalog.get(code)

    def _throttled(self, code: Code, ts: int) -> bool:
        anterior = self._last_issued.get(code)
        return anterior is not None and ts - anterior < self.throttle_ms

    @staticmethod
    def _severity(entrada: CatalogEntry, sinal: Any) -> Severity:
        """A severidade do sinal manda quando existe; senão vale a do catálogo."""
        if isinstance(sinal, SceneWarning):
            return sinal.severity
        return entrada.severity
