"""
Executar com:
python manage.py shell -c "exec(open('scripts/remove_demo_data.py', encoding='utf-8').read())"
"""

import os

from django.apps import apps
from django.db import transaction
from django.db.models import Q


# ============================================================
# HELPERS
# ============================================================

def get_model(app_label, model_name):
    try:
        return apps.get_model(app_label, model_name)
    except LookupError:
        return None


def importar_user():
    try:
        from apps.user.models import User
        return User
    except Exception:
        return get_model("users", "User") or get_model("user", "User")


def apagar_firebase_demo_users():
    try:
        import firebase_admin
        from firebase_admin import credentials, auth
    except ImportError:
        print("[FIREBASE] firebase-admin não instalado. A saltar remoção no Firebase.")
        return

    service_account_path = "firebase-adminsdk.json"

    if not os.path.exists(service_account_path):
        print("[FIREBASE] firebase-adminsdk.json não encontrado. A saltar remoção no Firebase.")
        return

    if not firebase_admin._apps:
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred)

    emails_demo = []

    for prefixo in ["gestor_demo_", "cliente_demo_", "motorista_demo_"]:
        for i in range(1, 101):
            emails_demo.append(f"{prefixo}{i}@hermez.com")

    apagados = 0
    ignorados = 0

    for email in emails_demo:
        try:
            user = auth.get_user_by_email(email)
            auth.delete_user(user.uid)
            apagados += 1
            print(f"[FIREBASE APAGADO] {email}")
        except auth.UserNotFoundError:
            ignorados += 1
        except Exception as e:
            print(f"[FIREBASE ERRO] {email}: {e}")

    print(f"[FIREBASE] Apagados: {apagados}. Ignorados/não existentes: {ignorados}.")


# ============================================================
# MODELOS
# ============================================================

User = importar_user()
Client = get_model("client", "Client")
Driver = get_model("driver", "Driver")
Taxi = get_model("taxi", "Taxi")
Trip = get_model("trip", "Trip")
Invoice = get_model("invoice", "Invoice")
Refuel = get_model("refuel", "Refuel")
Shift = get_model("shift", "Shift")

if not User:
    raise RuntimeError("Modelo User não encontrado.")


# ============================================================
# REMOÇÃO
# ============================================================

print("A remover dados demo...")

demo_user_filter = (
    Q(username__contains="_demo_")
    | Q(email__contains="_demo_")
    | Q(username__startswith="cliente_demo_")
    | Q(username__startswith="motorista_demo_")
    | Q(username__startswith="gestor_demo_")
    | Q(email__startswith="cliente_demo_")
    | Q(email__startswith="motorista_demo_")
    | Q(email__startswith="gestor_demo_")
)

demo_users = User.objects.filter(demo_user_filter)
demo_user_ids = list(demo_users.values_list("id", flat=True))

print(f"Users demo encontrados na BD: {len(demo_user_ids)}")

with transaction.atomic():
    if Invoice and Trip:
        apagadas = Invoice.objects.filter(
            Q(trip__client_id__in=demo_user_ids)
            | Q(trip__driver_id__in=demo_user_ids)
        ).delete()
        print(f"Faturas demo removidas: {apagadas[0]}")

    if Refuel and Shift:
        apagados = Refuel.objects.filter(
            Q(shift__driver_id__in=demo_user_ids)
        ).delete()
        print(f"Reabastecimentos demo removidos: {apagados[0]}")

    if Trip:
        apagadas = Trip.objects.filter(
            Q(client_id__in=demo_user_ids)
            | Q(driver_id__in=demo_user_ids)
        ).delete()
        print(f"Viagens demo removidas: {apagadas[0]}")

    if Shift:
        apagados = Shift.objects.filter(
            Q(driver_id__in=demo_user_ids)
        ).delete()
        print(f"Turnos demo removidos: {apagados[0]}")

    apagados = demo_users.delete()
    print(f"Users demo removidos da BD: {apagados[0]}")

print("\nRemoção da base de dados concluída.")

apagar_firebase_demo_users()

print("\nRemoção concluída.")