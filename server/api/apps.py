from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"

    def ready(self) -> None:
        """Liga a invalidação do snapshot de configuração (SPEC-018, T-073).

        Em `ready` e não na importação do `models.py` porque é aqui que o Django garante que o
        app é carregado uma vez só — conectar signal no módulo os duplicaria sob autoreload, e o
        sintoma seria a versão da configuração pulando de dois em dois. O `dispatch_uid` é a
        segunda trava do mesmo problema.
        """
        from django.db.models.signals import post_delete, post_save

        from api.config import invalidate_snapshot
        from api.models import Plan, SiteConfig

        for modelo in (Plan, SiteConfig):
            post_save.connect(
                invalidate_snapshot, sender=modelo, dispatch_uid=f"df-config-save-{modelo.__name__}"
            )
            post_delete.connect(
                invalidate_snapshot, sender=modelo, dispatch_uid=f"df-config-del-{modelo.__name__}"
            )
