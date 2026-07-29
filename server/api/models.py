"""Persistência da API (SPEC-010 e SPEC-011).

Três tabelas, com papéis bem distintos:

- `SessionResult` — o relatório consolidado, escrito pelo **report-builder** a partir dos
  eventos (SPEC-010). Não sabe de usuário e não pode saber: ele é derivável 100% por replay
  do stream, e um replay não conhece quem estava logado.
- `SessionClaim` — de quem é a sessão (SPEC-011). Escrita pela **API** na admissão, que é o
  único momento em que o dono é conhecido. Tabela separada justamente para manter a de cima
  replayável.
- `User` — conta de e-mail e senha (SPEC-011).

A sessão **em andamento** continua em Redis com TTL (`api/sessions.py`); o Postgres guarda o
que sobrevive ao fim dela.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models

__all__ = ["SessionClaim", "SessionResult", "User"]


class UserManager(BaseUserManager):
    """Criação de conta com e-mail normalizado."""

    def create_user(self, email: str, password: str, **extra) -> User:
        if not email:
            raise ValueError("e-mail obrigatorio")
        # `lower()` além do `normalize_email` (que só baixa o domínio): duas contas separadas
        # por maiúscula no local-part seriam a mesma pessoa tentando entrar e não conseguindo.
        usuario = self.model(email=self.normalize_email(email).lower(), **extra)
        usuario.password = make_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_superuser(self, email: str, password: str, **extra) -> User:
        """Conta com as ferramentas de diagnóstico ligadas (`manage.py createsuperuser`).

        Não existia até a T-048, e a ausência era defensável enquanto "admin" não significava
        nada aqui — não há `django.contrib.admin` neste projeto. Com o `is_admin` da T-048 o
        conceito passou a existir, e `createsuperuser` é o primeiro comando que qualquer um
        tenta: deixá-lo estourando `AttributeError` seria esconder a porta certa atrás de um
        erro de programação.

        **Não** é superusuário no sentido do Django: não há painel, permissões nem grupos. O
        que esta conta ganha é a superfície de dev do cliente. As rotas continuam filtrando
        por dono da sessão — ela não lê o histórico de mais ninguém.
        """
        extra.setdefault("is_admin", True)
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser):
    """Conta do produto (SPEC-011, Fase Inicial): e-mail + senha, sem mais nada.

    `AbstractBaseUser` e **não** `AbstractUser`: o modelo padrão do Django traz `username`
    (obrigatório e único, enquanto a spec autentica por e-mail), `first_name`/`last_name` e a
    árvore de permissões do admin. Nada disso tem uso aqui, e cada campo herdado é uma
    migration a mais para sempre.

    Sem `PermissionsMixin` pelo mesmo motivo: não há admin nem grupos. Se um painel nascer,
    ele adiciona o mixin com uma migration — o caminho inverso (arrancar permissões de um
    modelo em produção) é que seria caro.
    """

    email = models.EmailField(unique=True, max_length=254)
    #: Como a pessoa quer ser chamada no HUD. Opcional: pedir nome no cadastro é fricção, e o
    #: funil da SPEC-011 é o produto.
    name = models.CharField(max_length=80, blank=True)
    is_active = models.BooleanField(default=True)
    #: Vê as ferramentas de diagnóstico no cliente, inclusive em produção (T-048). Chamado
    #: `is_admin` e não `is_staff` de propósito: `is_staff` é o campo que o admin do Django
    #: consulta, e não há admin aqui — reusar o nome prometeria uma semântica que o projeto
    #: não tem. Não dá acesso a dado de ninguém: as rotas continuam por dono da sessão.
    is_admin = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        db_table = "app_user"

    def __str__(self) -> str:
        return self.email

    def to_dict(self) -> dict[str, object]:
        """Corpo do `GET /api/me` e do bloco `user` das respostas de auth."""
        return {
            "id": self.pk,
            "email": self.email,
            "name": self.name,
            "is_admin": self.is_admin,
            "date_joined": self.date_joined.isoformat(),
        }


class SessionClaim(models.Model):
    """De quem é a sessão, registrado na admissão (SPEC-011).

    `user` nulo é o caso normal e não é exceção: a Fase 0 inteira é anônima e o trial existe
    para que continue sendo — a conta é o degrau seguinte do funil, não o pedágio da entrada.

    `device_id` é o que o trial conta (3 sessões/dia). Fica aqui, e não só no contador do
    Redis, porque o contador expira e a pergunta "quantas sessões este aparelho já fez?"
    sobrevive a ele.
    """

    session_id = models.CharField(max_length=64, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    device_id = models.CharField(max_length=64, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "session_claim"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.session_id} · {self.user or 'anonimo'}"


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
