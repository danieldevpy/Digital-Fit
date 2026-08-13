"""Replay de keypoints contra a stack de verdade (T-133 / SPEC-012).

## A perna que faltava, e por que ela não é a do navegador

A T-040 desenhou a terceira perna da paridade como um arquivo exportado pelo painel de dev do
cliente. Funciona, e continua valendo — mas é **manual por construção**: alguém precisa abrir o
navegador, escolher o vídeo, esperar 30 s e baixar o JSON. Uma medição que depende disso não
roda em gate nenhum, e foi por isso que a pendência da T-040 ficou aberta por semanas enquanto
uma afirmação errada sobre o agachamento envelhecia no manifest.

Este módulo mede outra coisa, e é justamente o que estava sem instrumento:

| perna | quem extrai a pose | quem conta | automatizável |
|---|---|---|---|
| bancada (`evalctl run`) | MediaPipe do Python | `analyze_frames`, em processo | sim |
| **stack (`evalctl stack`)** | ninguém: keypoints prontos | **os serviços no ar** | **sim** |
| navegador (`--browser`) | MediaPipe WASM/GPU | os mesmos serviços | não |

"Os serviços no ar" são api + gateway + analysis-worker + report-builder, pelo compose.

A bancada prova a FSM. O navegador prova a extração. **Entre as duas havia um vão**: admissão,
WebSocket, msgpack, janela de 30 s, preparação, relógio do servidor, tombstone — tudo isso só
existe no caminho real, e nada disso era medido por nada.

Alimentar a stack com uma fixture (keypoints que a bancada já contou) é o que separa "o servidor
conta errado" de "o navegador extrai diferente": as duas hipóteses ficavam grudadas enquanto a
única medição de ponta a ponta passava pelo MediaPipe do navegador.

## O que esperar dos números

A contagem daqui é MENOR que a da bancada, e isso não é erro: a sessão real tem preparação
(T-049) e teto de 30 s (SPEC-009), então um vídeo de 36 s entra pela metade do fim. Comparar
com a bancada exige lembrar disso — o que se compara de igual para igual é **stack × navegador**,
que veem a mesma janela.

Precisa da stack de pé (`docker compose up`) e não roda em CI: é medição de integração, feita
por quem está investigando.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import msgpack

from workers.shared.events import EventType, Source
from workers.shared.keypoints import KeypointFixture, load_fixture

__all__ = ["StackResult", "build_frame_envelope", "replay_fixture", "request_ticket"]

PROTOCOL_VERSION = 1

#: Quanto esperar pelo `session.report.ready` depois do último frame. O servidor fecha a sessão
#: pelo teto de 30 s; este prazo é só a margem da volta.
REPORT_TIMEOUT_S = 20.0


@dataclass(slots=True)
class StackResult:
    """O que a stack devolveu para uma fixture."""

    label: str
    exercise: str
    session_id: str
    reps: int
    reason: str
    frames_sent: int
    expected_reps: int | None = None
    rep_durations_ms: list[int] = field(default_factory=list)
    scene_warnings: dict[str, int] = field(default_factory=dict)
    calibration: dict[str, Any] = field(default_factory=dict)

    def summary_line(self) -> str:
        rotulo = "?" if self.expected_reps is None else str(self.expected_reps)
        return (
            f"{self.label} ({self.exercise}): {self.reps} reps "
            f"[rotulo {rotulo}] · {self.reason} · {self.frames_sent} frames"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.label,
            "exercise": self.exercise,
            "session_id": self.session_id,
            "reps": self.reps,
            "expected_reps": self.expected_reps,
            "reason": self.reason,
            "frames": self.frames_sent,
            "rep_durations_ms": self.rep_durations_ms,
            "quality_signals": self.scene_warnings,
            "calibration": self.calibration,
            "source": "stack",
        }


def build_frame_envelope(session_id: str, seq: int, ts_ms: int, landmarks: Any) -> dict[str, Any]:
    """Envelope de `pose.frame` idêntico ao que o cliente monta (`web/src/lib/events.ts`).

    Puro de propósito: é a única parte deste módulo que dá para testar sem stack de pé, e é
    também a que erra silenciosamente — foi mandar isto como texto em vez de msgpack que fez a
    primeira medição devolver zero evento e parecer, por um instante, um bug do servidor.
    """
    return {
        "v": PROTOCOL_VERSION,
        "type": EventType.POSE_FRAME.value,
        "session_id": session_id,
        "ts": ts_ms,
        "seq": seq,
        "source": Source.EDGE.value,
        "data": {"landmarks": landmarks},
    }


def request_ticket(api: str, exercise: str, *, countdown_s: int, device_id: str) -> dict[str, Any]:
    """`POST /api/sessions` como o cliente faz (SPEC-009/T-011): o ticket manda em tudo.

    `urllib` e não `httpx`: uma dependência a mais na bancada por uma única chamada POST seria
    caro demais pelo que entrega.
    """
    corpo = json.dumps(
        {
            "exercise": exercise,
            "requested_mode": "edge",
            "countdown_s": countdown_s,
            "probe_result": None,
        }
    ).encode("utf-8")
    pedido = urllib.request.Request(
        f"{api.rstrip('/')}/api/sessions",
        data=corpo,
        headers={"Content-Type": "application/json", "X-Device-Id": device_id},
        method="POST",
    )
    try:
        with urllib.request.urlopen(pedido, timeout=30) as resposta:
            return json.loads(resposta.read())
    except urllib.error.HTTPError as exc:
        detalhe = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"admissao recusada ({exc.code}): {detalhe}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"api fora do ar em {api}: {exc.reason}") from exc


async def replay_fixture(
    fixture: KeypointFixture,
    *,
    api: str = "http://localhost:8000",
    exercise: str | None = None,
    countdown_s: int = 3,
    device_id: str = "evalctl-stack",
    on_event: Any = None,
) -> StackResult:
    """Toca a fixture pelo caminho real e devolve o que a stack contou.

    Em **tempo real**, e não o mais rápido possível: quem decide o fim da sessão é o relógio do
    servidor (SPEC-009), então despejar 548 frames em dois segundos mediria uma sessão que não
    existe para ninguém.
    """
    import websockets

    slug = exercise or fixture.exercise
    ticket = request_ticket(api, slug, countdown_s=countdown_s, device_id=device_id)
    session_id = ticket["session_id"]

    recebidos: list[dict[str, Any]] = []
    fim = asyncio.Event()

    async with websockets.connect(ticket["ws_url"], max_size=None) as ws:

        async def ouvir() -> None:
            try:
                async for bruto in ws:
                    evento = (
                        msgpack.unpackb(bruto, raw=False)
                        if isinstance(bruto, bytes | bytearray)
                        else json.loads(bruto)
                    )
                    recebidos.append(evento)
                    if on_event is not None:
                        on_event(evento)
                    if evento.get("type") == EventType.SESSION_REPORT_READY.value:
                        fim.set()
            except websockets.ConnectionClosed:
                fim.set()

        escuta = asyncio.create_task(ouvir())
        inicio = time.monotonic()
        enviados = 0
        try:
            for indice, quadro in enumerate(fixture.frames):
                atraso = inicio + quadro.ts / 1000.0 - time.monotonic()
                if atraso > 0:
                    await asyncio.sleep(atraso)
                if fim.is_set():
                    break
                envelope = build_frame_envelope(
                    session_id, indice, int(time.time() * 1000), quadro.landmarks
                )
                try:
                    await ws.send(msgpack.packb(envelope, use_bin_type=True))
                except websockets.ConnectionClosed:
                    break
                enviados += 1
            # Prazo estourado não é erro: a sessão pode ter morrido de `no_data` sem relatório,
            # e esse silêncio é ele mesmo um resultado — volta como `reason`.
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(fim.wait(), timeout=REPORT_TIMEOUT_S)
        finally:
            escuta.cancel()

    return _resultado(fixture, slug, session_id, enviados, recebidos)


def _resultado(
    fixture: KeypointFixture,
    slug: str,
    session_id: str,
    enviados: int,
    eventos: list[dict[str, Any]],
) -> StackResult:
    completed = next(
        (e for e in eventos if e.get("type") == EventType.SESSION_COMPLETED.value), None
    )
    calibrated = next(
        (e for e in eventos if e.get("type") == EventType.SESSION_CALIBRATED.value), None
    )
    reps = [e for e in eventos if e.get("type") == EventType.REP_DETECTED.value]

    avisos: dict[str, int] = {}
    for evento in eventos:
        if evento.get("type") != EventType.SCENE_WARNING.value:
            continue
        codigo = str(evento.get("data", {}).get("code", "?"))
        avisos[codigo] = avisos.get(codigo, 0) + 1

    dados = (completed or {}).get("data", {})
    return StackResult(
        label=fixture.label,
        exercise=slug,
        session_id=session_id,
        # `session.completed` é a fonte; a contagem dos `rep.detected` é só a checagem de que
        # nenhum evento se perdeu no caminho.
        reps=int(dados.get("rep_count", len(reps))),
        reason=str(dados.get("reason", "sem session.completed")),
        frames_sent=enviados,
        expected_reps=fixture.expected_reps,
        rep_durations_ms=list(dados.get("rep_durations_ms") or []),
        scene_warnings=avisos,
        calibration=dict((calibrated or {}).get("data", {})),
    )


def cmd_stack(args: argparse.Namespace) -> int:
    """Subcomando `evalctl stack`. Código 1 quando a sessão não chegou a `completed`."""
    caminho = Path(args.fixture)
    if not caminho.exists():
        print(f"fixture nao encontrada: {caminho}")
        return 2

    fixture = load_fixture(caminho)

    def eco(evento: dict[str, Any]) -> None:
        tipo = evento.get("type")
        if tipo in {
            EventType.SESSION_CALIBRATED.value,
            EventType.SESSION_COMPLETED.value,
        }:
            print(f"  <- {tipo} {json.dumps(evento.get('data'), ensure_ascii=False)[:160]}")

    resultado = asyncio.run(
        replay_fixture(
            fixture,
            api=args.api,
            exercise=args.exercise,
            countdown_s=args.countdown_s,
            device_id=args.device,
            on_event=None if args.quiet else eco,
        )
    )

    if not args.quiet:
        print(resultado.summary_line())
        if resultado.scene_warnings:
            print(f"  avisos de cena: {resultado.scene_warnings}")

    if args.report:
        destino = Path(args.report)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(
            json.dumps(resultado.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        if not args.quiet:
            print(f"relatorio: {destino}")

    return 0 if resultado.reason == "completed" else 1
