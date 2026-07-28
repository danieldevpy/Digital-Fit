"""Regra do pose-worker: `frame.raw` entra, `pose.frame` sai (SPEC-005, T-016).

Separado do loop de Redis para ser testável sem barramento e sem MediaPipe — o extractor é
injetado. O que importa aqui é a política: o que vira `pose.frame`, o que é descartado, e
por quê.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from workers.pose_worker.extractor import PoseExtractor
from workers.shared.events import (
    Envelope,
    EventType,
    FrameRaw,
    PoseFrame,
    Source,
    make_envelope,
)

__all__ = ["MAX_AGE_MS", "PoseRouter", "PoseStats"]

logger = logging.getLogger("pose-worker")

#: Frame que esperou mais que isto na fila é descartado (SPEC-005): análise em tempo real não
#: quer frame velho — processá-lo gastaria o vCPU para produzir feedback sobre o passado.
MAX_AGE_MS = 500


@dataclass
class PoseStats:
    """Contadores do processo. Só observabilidade; nada de decisão depende deles."""

    processed: int = 0
    stale: int = 0
    no_pose: int = 0
    failed: int = 0
    ignored: int = 0
    #: Idade do frame mais velho já aceito — ajuda a ver a fila encostando no teto.
    max_age_ms: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "processed": self.processed,
            "stale": self.stale,
            "no_pose": self.no_pose,
            "failed": self.failed,
            "ignored": self.ignored,
            "max_age_ms": self.max_age_ms,
        }


@dataclass
class PoseRouter:
    """Transforma `frame.raw` em `pose.frame`. Sem estado por sessão — ver `extractor.py`."""

    extractor: PoseExtractor
    max_age_ms: int = MAX_AGE_MS
    stats: PoseStats = field(default_factory=PoseStats)
    _avisou_relogio: bool = False

    def handle(self, envelope: Envelope, *, now_ms: int | None = None) -> list[Envelope]:
        """Zero ou um `pose.frame`. Nunca levanta: erro vira contador e log."""
        if envelope.type is not EventType.FRAME_RAW:
            # `frames.raw` é um stream de propósito único; qualquer outra coisa aqui é bug de
            # quem publicou, não deste worker.
            self.stats.ignored += 1
            logger.warning("tipo inesperado em frames.raw: %s", envelope.type.value)
            return []

        agora = now_ms if now_ms is not None else int(time.time() * 1000)
        idade = agora - envelope.ts

        # A idade é medida com o `ts` do envelope, como a SPEC-005 manda nas notas técnicas.
        # O preço: `ts` é o relógio do CLIENTE. Um celular atrasado faz todo frame parecer
        # velho e o worker descarta a sessão inteira em silêncio — por isso o aviso abaixo,
        # que transforma um sumiço inexplicável em uma linha de log. (Ver "Descobertas" no
        # BACKLOG: medir pelo ID da entrada do stream seria imune a isso.)
        if idade < -self.max_age_ms and not self._avisou_relogio:
            self._avisou_relogio = True
            logger.warning(
                "frame da sessao %s chegou %dms no FUTURO: relogio do cliente adiantado; "
                "o descarte por idade fica sem sentido nesta sessao",
                envelope.session_id,
                -idade,
            )

        if idade > self.max_age_ms:
            self.stats.stale += 1
            return []

        try:
            frame = FrameRaw.from_data(envelope.data)
            landmarks = self.extractor.extract(frame.jpeg)
        except Exception:
            self.stats.failed += 1
            logger.exception(
                "falha ao extrair pose da sessao %s (seq %s)", envelope.session_id, envelope.seq
            )
            return []

        if landmarks is None:
            # Ninguém no quadro. Não é erro: a validação de cena (SPEC-003) é quem reclama,
            # e ela só reclama se receber frames — então não inventamos um `pose.frame` vazio.
            self.stats.no_pose += 1
            return []

        self.stats.processed += 1
        self.stats.max_age_ms = max(self.stats.max_age_ms, idade)

        # `ts` e `seq` são os do frame original: o tempo que importa para a FSM é quando a
        # imagem foi capturada, não quando o servidor terminou de processá-la.
        return [
            make_envelope(
                PoseFrame(landmarks=landmarks),
                session_id=envelope.session_id,
                ts=envelope.ts,
                seq=envelope.seq,
                source=Source.CLOUD,
            )
        ]
