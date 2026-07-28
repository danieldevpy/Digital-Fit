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

#: A partir deste desvio entre o relógio do cliente e o do servidor, sai um aviso (uma vez por
#: worker). Meio segundo é folgado para skew normal e apertado para relógio realmente errado.
_AVISO_DESVIO_MS = 500


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

    def handle(
        self,
        envelope: Envelope,
        *,
        arrived_ms: int | None = None,
        now_ms: int | None = None,
    ) -> list[Envelope]:
        """Zero ou um `pose.frame`. Nunca levanta: erro vira contador e log.

        `arrived_ms` é a hora de ENTRADA no stream, do relógio do servidor (vem do ID da
        entrada do Redis). É com ela que a espera na fila é medida — ver a nota abaixo.
        """
        if envelope.type is not EventType.FRAME_RAW:
            # `frames.raw` é um stream de propósito único; qualquer outra coisa aqui é bug de
            # quem publicou, não deste worker.
            self.stats.ignored += 1
            logger.warning("tipo inesperado em frames.raw: %s", envelope.type.value)
            return []

        agora = now_ms if now_ms is not None else int(time.time() * 1000)

        # Espera na fila com o relógio do SERVIDOR nas duas pontas (SPEC-005, notas técnicas).
        # Usar o `ts` do envelope aqui seria comparar relógios de máquinas diferentes: `ts` é
        # carimbado pelo navegador, e um celular atrasado faria todo frame parecer velho —
        # a sessão inteira sumiria sem nada no log explicando.
        referencia = arrived_ms if arrived_ms is not None else envelope.ts
        idade = agora - referencia

        # Diagnóstico, não decisão: divergência grande entre o relógio do cliente e o nosso
        # não muda mais nada aqui, mas explica latência estranha em `pose.frame` mais adiante.
        desvio = agora - envelope.ts
        if abs(desvio) > _AVISO_DESVIO_MS and not self._avisou_relogio:
            self._avisou_relogio = True
            logger.warning(
                "relogio do cliente da sessao %s difere do servidor em %dms; "
                "o descarte por idade nao depende disso, mas o `ts` dos eventos sim",
                envelope.session_id,
                desvio,
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
