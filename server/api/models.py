"""Persistência da Fase 0 (SPEC-010).

Só o resultado consolidado da sessão. A sessão **em andamento** vive em Redis com TTL
(`api/sessions.py`) — o Postgres guarda o que sobrevive ao fim dela.
"""

from __future__ import annotations

from django.db import models

__all__ = ["SessionResult"]


class SessionResult(models.Model):
    """Relatório consolidado de uma sessão de 30 s.

    `session_id` é único e é a chave de negócio: o report-builder faz upsert por ele. Isso é o
    que permite reprocessar o mesmo `session.completed` — depois de um crash, ou num replay do
    stream — sem criar duas linhas para a mesma sessão (SPEC-010, critério 2).

    `CharField` e não `UUIDField`: o id vem do envelope, e nem todo produtor de eventos é a
    API. A bancada de avaliação (SPEC-012) usa ids legíveis como `polichinelo-01`, e um campo
    UUID recusaria persistir justamente as sessões que servem para medir o sistema.
    """

    session_id = models.CharField(max_length=64, unique=True)
    exercise = models.CharField(max_length=40)
    mode = models.CharField(max_length=16)
    #: `SessionEndReason` do contrato. Guardado como texto: o motivo é dado do relatório, e um
    #: enum do banco obrigaria migration a cada motivo novo.
    reason = models.CharField(max_length=16)

    rep_count = models.PositiveIntegerField(default=0)
    #: Duração **efetiva**: da calibração ao fim. Não é o tempo de conexão.
    duration_ms = models.PositiveIntegerField(default=0)
    cadence_rpm = models.FloatField(default=0.0)

    cadence_windows = models.JSONField(default=list)
    rep_durations_ms = models.JSONField(default=list)
    feedback_counts = models.JSONField(default=dict)
    scene_warning_counts = models.JSONField(default=dict)
    calibration_samples = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "session_result"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.session_id} · {self.exercise} · {self.rep_count} reps"

    def to_report(self) -> dict[str, object]:
        """Corpo do `GET /api/sessions/{id}/report`.

        Campos em snake_case, iguais aos do contrato de eventos: o cliente já lê o fio nesse
        formato, e traduzir aqui criaria uma segunda convenção para os mesmos dados.
        """
        return {
            "session_id": self.session_id,
            "exercise": self.exercise,
            "mode": self.mode,
            "reason": self.reason,
            "rep_count": self.rep_count,
            "duration_ms": self.duration_ms,
            "cadence_rpm": self.cadence_rpm,
            "cadence_windows": self.cadence_windows,
            "rep_durations_ms": self.rep_durations_ms,
            "feedback_counts": self.feedback_counts,
            "scene_warning_counts": self.scene_warning_counts,
            "calibration_samples": self.calibration_samples,
            "created_at": self.created_at.isoformat(),
        }
