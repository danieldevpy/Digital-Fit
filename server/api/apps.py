from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"
    #: Título do grupo no painel. Sem isto o Django escreve "Api", que é o nome do pacote
    #: Python — informação de quem escreve o código, na tela de quem opera o produto.
    verbose_name = "Digital Fit"

    def ready(self) -> None:
        """Liga as invalidações de cache: configuração (SPEC-018, T-073) e engajamento (T-086).

        Em `ready` e não na importação do `models.py` porque é aqui que o Django garante que o
        app é carregado uma vez só — conectar signal no módulo os duplicaria sob autoreload, e o
        sintoma seria a versão da configuração pulando de dois em dois. O `dispatch_uid` é a
        segunda trava do mesmo problema.
        """
        from django.db.models.signals import post_delete, post_save

        from api.config import invalidate_snapshot
        from api.engagement_cache import invalidar_por_resultado, invalidar_por_usuario
        from api.models import Exercise, ExerciseGuideStep, Plan, SessionResult, SiteConfig, User

        # SPEC-019: o corpo do `GET /api/engagement` muda por duas escritas — relatório novo (o
        # report-builder roda como comando do Django, então o signal dispara no processo certo e
        # o Redis é o mesmo) e edição da conta (meta diária, plano). A terceira coisa que o muda
        # é a meia-noite, e essa não tem signal: quem cuida dela é a data na chave do cache.
        post_save.connect(
            invalidar_por_resultado, sender=SessionResult, dispatch_uid="df-eng-result"
        )
        post_save.connect(invalidar_por_usuario, sender=User, dispatch_uid="df-eng-user")

        # `ExerciseGuideStep` entra na lista porque os passos viajam **dentro** do exercício no
        # `GET /api/config`: editar um passo sem invalidar deixaria o Guia servindo o texto
        # antigo, e ninguém ligaria uma coisa à outra ao procurar o motivo.
        for modelo in (Plan, SiteConfig, Exercise, ExerciseGuideStep):
            post_save.connect(
                invalidate_snapshot, sender=modelo, dispatch_uid=f"df-config-save-{modelo.__name__}"
            )
            post_delete.connect(
                invalidate_snapshot, sender=modelo, dispatch_uid=f"df-config-del-{modelo.__name__}"
            )
