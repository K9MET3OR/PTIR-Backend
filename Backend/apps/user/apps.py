from django.apps import AppConfig


class UserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.user'
    label = 'users'

    def ready(self):
        # Inicializar Firebase Admin SDK quando a app carrega
        from . import firebase_init
