"""
Executar com:
python manage.py shell -c "exec(open('scripts/sync_firebase_users.py', encoding='utf-8').read())"
"""

import os
import firebase_admin
from firebase_admin import credentials, auth

from apps.user.models import User


PASSWORD_DEMO = "123456"
SERVICE_ACCOUNT_PATH = "firebase-adminsdk.json"


def inicializar_firebase():
    if firebase_admin._apps:
        return

    if not os.path.exists(SERVICE_ACCOUNT_PATH):
        raise FileNotFoundError(
            f"Ficheiro {SERVICE_ACCOUNT_PATH} não encontrado. "
            "Coloca o JSON da service account na raiz do backend."
        )

    cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
    firebase_admin.initialize_app(cred)


def criar_ou_atualizar_firebase_user(user):
    email = user.email
    username = user.username or email.split("@")[0]

    if not email:
        print(f"[IGNORADO] User sem email: {user}")
        return

    try:
        firebase_user = auth.get_user_by_email(email)

        auth.update_user(
            firebase_user.uid,
            password=PASSWORD_DEMO,
            display_name=getattr(user, "name", None) or getattr(user, "nome", None) or username,
            disabled=False,
        )

        print(f"[ATUALIZADO] {email}")

    except auth.UserNotFoundError:
        firebase_user = auth.create_user(
            email=email,
            password=PASSWORD_DEMO,
            display_name=getattr(user, "name", None) or getattr(user, "nome", None) or username,
            disabled=False,
        )

        print(f"[CRIADO] {email}")

    except Exception as e:
        print(f"[ERRO] {email}: {e}")


inicializar_firebase()

demo_users = User.objects.filter(email__contains="_demo_").order_by("email")

print(f"A sincronizar {demo_users.count()} utilizadores demo com o Firebase...\n")

for user in demo_users:
    criar_ou_atualizar_firebase_user(user)

print("\nSincronização concluída.")
print(f"Password usada para todos: {PASSWORD_DEMO}")