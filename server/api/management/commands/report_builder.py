"""report-builder: consome `events.analysis` e persiste o relatório da sessão (SPEC-010).

    python manage.py report_builder

Por que este consumidor mora **dentro do Django** e não em `workers/`, como os outros: ele é
o único que escreve no Postgres, e o ORM (com migrations, transações e o mesmo `SessionResult`
que a API lê) vive aqui. Um worker separado teria de importar `server/` — invertendo a
dependência que o resto do repositório mantém em uma direção só (server → workers). Ver
ADR-008. A consolidação em si continua pura e sem Django, em
`workers/report_builder/builder.py`; este arquivo é encanamento.

Precedente: `gateway/relay.py` já é um consumidor de stream rodando dentro do Django.
"""

from __future__ import annotations

import logging
import os
import signal
from types import FrameType
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand

from workers.report_builder.builder import ReportAccumulator, SessionReport
from workers.shared.bus import EventBus, RedisBus
from workers.shared.events import (
    Envelope,
    EventType,
    SessionReportReady,
    Source,
    Stream,
    make_envelope,
)

logger = logging.getLogger("report-builder")

GROUP = "report"
BLOCK_MS = 1000
BATCH = 100

#: Nome **estável** de propósito (nada de PID nem hostname dentro). O PEL do Redis é indexado
#: por nome de consumidor: com um nome novo a cada restart, tudo que estava pendente ficaria
#: órfão e o critério 2 da SPEC-010 seria falso na prática, sem nenhum erro aparecendo.
DEFAULT_CONSUMER = "report-builder"

#: Sessão sem nenhum evento por tanto tempo nunca vai fechar (o worker que a fecharia morreu
#: antes de emitir o `session.completed`). Evacuar libera memória e confirma as mensagens, que
#: senão ficariam pendentes para sempre bloqueando o PEL.
STALE_MS = 5 * 60_000


class Command(BaseCommand):
    help = "Consolida sessões de events.analysis em SessionResult (SPEC-010)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--consumer", default=os.environ.get("CONSUMER_NAME", DEFAULT_CONSUMER))
        parser.add_argument(
            "--max-batches",
            type=int,
            default=None,
            help="Encerra depois de N lotes (usado em teste e em replay pontual).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        logging.basicConfig(
            level=os.environ.get("LOG_LEVEL", "INFO"),
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
        bus = RedisBus.from_url(settings.REDIS_URL)
        worker = ReportWorker(bus, consumer=options["consumer"])
        parada = Shutdown()
        parada.install()
        logger.info("report-builder de pe (%s) lendo %s", worker.consumer, Stream.EVENTS_ANALYSIS)
        try:
            worker.run(shutdown=parada, max_batches=options["max_batches"])
        finally:
            bus.close()
        logger.info("report-builder encerrado: %s relatorios escritos", worker.written)


class Shutdown:
    """SIGTERM/SIGINT: termina o lote e sai (o compose reinicia)."""

    def __init__(self) -> None:
        self.requested = False

    def install(self) -> None:
        for sinal in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sinal, self._handle)

    def _handle(self, signum: int, frame: FrameType | None) -> None:
        del frame
        logger.info("sinal %s recebido, encerrando apos o lote atual", signum)
        self.requested = True


class ReportWorker:
    """Loop de consumo. Separado do `Command` para ser testável com o barramento em memória."""

    def __init__(self, bus: EventBus, *, consumer: str = DEFAULT_CONSUMER, sink=None) -> None:
        self.bus = bus
        self.consumer = consumer
        self.accumulator = ReportAccumulator()
        #: Onde o relatório é gravado. Injetável para o teste não precisar de banco quando o
        #: que está sendo testado é o loop, e não o ORM.
        self.sink = sink or persist
        #: Mensagens de cada sessão ainda sem ack. O ack só acontece quando o relatório está
        #: gravado — é isso que faz a promessa "nenhuma sessão sem relatório" ser verdadeira:
        #: se o processo morrer no meio, nada foi confirmado e tudo é reentregue.
        self._pendentes: dict[str, list[str]] = {}
        self.written = 0

    # ------------------------------------------------------------------ ciclo

    def start(self) -> int:
        """Cria o grupo e reprocessa o que ficou pendente de uma execução anterior."""
        self.bus.ensure_group(Stream.EVENTS_ANALYSIS, GROUP)
        pendentes = self.bus.consume_pending(
            Stream.EVENTS_ANALYSIS, group=GROUP, consumer=self.consumer, count=BATCH * 10
        )
        if pendentes:
            logger.info("reprocessando %s eventos pendentes do restart anterior", len(pendentes))
        for message_id, envelope in pendentes:
            self._processar(message_id, envelope)
        return len(pendentes)

    def run(self, *, shutdown: Shutdown | None = None, max_batches: int | None = None) -> None:
        shutdown = shutdown or Shutdown()
        self.start()
        lotes = 0
        while not shutdown.requested and (max_batches is None or lotes < max_batches):
            lotes += 1
            self.run_once()

    def run_once(self) -> int:
        """Um lote. Devolve quantos eventos foram consumidos."""
        lote = self.bus.consume(
            Stream.EVENTS_ANALYSIS,
            group=GROUP,
            consumer=self.consumer,
            block_ms=BLOCK_MS,
            count=BATCH,
        )
        for message_id, envelope in lote:
            self._processar(message_id, envelope)
        self._evacuar_velhas()
        return len(lote)

    # --------------------------------------------------------------- interno

    def _processar(self, message_id: str, envelope: Envelope, now_ms: int | None = None) -> None:
        # O sino do próprio builder volta pelo stream; confirmar e sair evita segurá-lo
        # pendente para sempre à espera de uma sessão que já fechou.
        if envelope.type is EventType.SESSION_REPORT_READY:
            self.bus.ack(Stream.EVENTS_ANALYSIS, GROUP, message_id)
            return

        self._pendentes.setdefault(envelope.session_id, []).append(message_id)
        try:
            relatorio = self.accumulator.push(envelope, now_ms=now_ms or _agora_ms())
        except Exception:
            # Um evento problemático não pode travar o stream: confirma o que se tinha da
            # sessão e segue. Perder um relatório é ruim; parar de gerar todos é pior.
            logger.exception("falha ao acumular %s (%s)", message_id, envelope.type)
            self._confirmar(envelope.session_id)
            self.accumulator.drop(envelope.session_id)
            return

        if relatorio is None:
            return

        try:
            self.sink(relatorio)
            self.written += 1
        except Exception:
            # Banco fora do ar: NÃO confirma. As mensagens ficam pendentes e a sessão será
            # reconstruída no próximo start — que é exatamente o comportamento prometido.
            logger.exception("falha ao gravar relatorio de %s", envelope.session_id)
            self.accumulator.drop(envelope.session_id)
            return

        logger.info(
            "relatorio de %s gravado: %s reps, %s ms, cadencia %.1f rpm",
            relatorio.session_id,
            relatorio.rep_count,
            relatorio.duration_ms,
            relatorio.cadence_rpm,
        )
        self._anunciar(envelope)
        self._confirmar(envelope.session_id)

    def _anunciar(self, completado: Envelope) -> None:
        """Publica `session.report.ready` — o cliente para de esperar e busca o relatório."""
        try:
            self.bus.publish(
                make_envelope(
                    SessionReportReady(),
                    session_id=completado.session_id,
                    ts=completado.ts,
                    # `seq` monotônico por sessão: este evento vem depois de tudo que o
                    # analysis-worker emitiu, e o `session.completed` foi o último deles.
                    seq=completado.seq + 1,
                    source=Source.SYSTEM,
                )
            )
        except Exception:
            # O relatório já está gravado. Sem o aviso o cliente cai no polling e mostra o
            # relatório mesmo assim — não é motivo para reprocessar a sessão.
            logger.exception("relatorio de %s gravado, mas o aviso falhou", completado.session_id)

    def _confirmar(self, session_id: str) -> None:
        for message_id in self._pendentes.pop(session_id, []):
            self.bus.ack(Stream.EVENTS_ANALYSIS, GROUP, message_id)

    def _evacuar_velhas(self, now_ms: int | None = None) -> list[str]:
        """Larga sessões que pararam de dar sinal — elas não vão fechar sozinhas."""
        agora = now_ms if now_ms is not None else _agora_ms()
        velhas = self.accumulator.stale(agora, max_age_ms=STALE_MS)
        for session_id in velhas:
            logger.info("sessao %s abandonada sem session.completed; descartada", session_id)
            self.accumulator.drop(session_id)
            self._confirmar(session_id)
        return velhas


def _agora_ms() -> int:
    """Relógio de parede do servidor. Único relógio que decide idade de sessão aqui."""
    import time

    return int(time.time() * 1000)


def persist(report: SessionReport) -> None:
    """Grava (ou regrava) o relatório.

    `update_or_create` e não `create`: o mesmo `session.completed` pode chegar duas vezes — num
    reprocessamento após crash ou num replay do stream — e a segunda vez tem de corrigir a
    linha, não explodir por chave duplicada nem duplicar a sessão.
    """
    from api.models import SessionResult

    dados = report.to_dict()
    dados.pop("session_id")
    SessionResult.objects.update_or_create(session_id=report.session_id, defaults=dados)
