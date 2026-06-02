"""Executar com:
pip install firebase-admin


python manage.py shell -c "exec(open('scripts/seed_demo_data.py', encoding='utf-8').read())"
"""

from datetime import timedelta
from decimal import Decimal

from django.apps import apps
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.db.models import Q, Max
from django.utils import timezone


# ============================================================
# CONFIGURAÇÃO
# ============================================================

TOTAL_CLIENTES = 45
TOTAL_MOTORISTAS = 20
TOTAL_ADMINS = 5
TOTAL_TAXIS = 10
TOTAL_VIAGENS = 20
TOTAL_FATURAS = 20
TOTAL_TURNOS_FUTUROS = 10
TOTAL_REABASTECIMENTOS = 15

PASSWORD_DEMO = "123456"


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


def campos_modelo(model):
    return {field.name for field in model._meta.fields}


def filtrar_campos(model, data):
    fields = campos_modelo(model)
    return {key: value for key, value in data.items() if key in fields}


def criar_objeto(model, defaults=None, **lookup):
    defaults = defaults or {}

    lookup_filtrado = filtrar_campos(model, lookup)
    defaults_filtrado = filtrar_campos(model, defaults)

    obj, created = model.objects.get_or_create(
        **lookup_filtrado,
        defaults=defaults_filtrado,
    )

    return obj, created


def nif_livre(base):
    nif = str(base).zfill(9)
    tentativa = int(nif)

    while User.objects.filter(nif=str(tentativa).zfill(9)).exists():
        tentativa += 1

    return str(tentativa).zfill(9)


def criar_user(username, email, role, name, nif=None):
    user = User.objects.filter(username=username).first()

    if user:
        return user

    data = {
        "username": username,
        "email": email,
        "name": name,
        "nome": name,
        "full_name": name,
        "role": role,
        "selectedRole": role,
        "nif": nif,
        "password": make_password(PASSWORD_DEMO),
    }

    data = filtrar_campos(User, data)

    user = User(**data)

    if hasattr(user, "set_password"):
        user.set_password(PASSWORD_DEMO)

    user.save()
    return user


def criar_client(username, email, name, nif, genero):
    if not Client:
        return criar_user(username, email, "cliente", name, nif)

    cliente = Client.objects.filter(username=username).first()

    if cliente:
        return cliente

    data = {
        "username": username,
        "email": email,
        "name": name,
        "nome": name,
        "full_name": name,
        "role": "cliente",
        "selectedRole": "cliente",
        "password": make_password(PASSWORD_DEMO),
        "nif": nif,
        "genero": genero,
        "telefone": "960000000",
        "localidade": "Lisboa",
        "codigo_postal": "1000-001",
    }

    data = filtrar_campos(Client, data)

    cliente = Client(**data)

    if hasattr(cliente, "set_password"):
        cliente.set_password(PASSWORD_DEMO)

    cliente.save()
    return cliente


def criar_driver(username, email, name, nif, i):
    if not Driver:
        return criar_user(username, email, "motorista", name, nif)

    driver = Driver.objects.filter(username=username).first()

    if driver:
        return driver

    data = {
        "username": username,
        "email": email,
        "name": name,
        "nome": name,
        "full_name": name,
        "role": "motorista",
        "selectedRole": "motorista",
        "password": make_password(PASSWORD_DEMO),
        "nif": nif,
        "ano_nascimento": 1980 + (i % 20),
        "genero": "M" if i % 2 else "F",
        "num_carta_conducao": f"DEMO-CARTA-{i:03d}",
        "validade_carta": timezone.now().date() + timedelta(days=365 * 5),
        "localidade": "Lisboa",
        "codigo_postal": "1000-001",
        "estado": "indisponivel",
        "telefone": f"91{i:07d}"[-9:],
    }

    data = filtrar_campos(Driver, data)

    driver = Driver(**data)

    if hasattr(driver, "set_password"):
        driver.set_password(PASSWORD_DEMO)

    driver.save()
    return driver


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
    raise RuntimeError("Modelo User não encontrado. Confirma o nome da app de utilizadores.")


# ============================================================
# LIMPEZA DE DADOS DEMO ANTIGOS
# ============================================================

print("A limpar dados demo antigos...")

with transaction.atomic():
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

    if Invoice and Trip:
        Invoice.objects.filter(
            Q(trip__client_id__in=demo_users.values_list("id", flat=True))
            | Q(trip__driver_id__in=demo_users.values_list("id", flat=True))
        ).delete()

    if Trip:
        Trip.objects.filter(
            Q(client_id__in=demo_users.values_list("id", flat=True))
            | Q(driver_id__in=demo_users.values_list("id", flat=True))
        ).delete()

    if Shift:
        Shift.objects.filter(
            Q(driver_id__in=demo_users.values_list("id", flat=True))
        ).delete()

    if demo_users.exists():
        demo_users.delete()


# ============================================================
# USERS / ADMINS
# ============================================================

print("A criar gestores...")

admins = []

for i in range(1, TOTAL_ADMINS + 1):
    admin = criar_user(
        username=f"gestor_demo_{i}",
        email=f"gestor_demo_{i}@hermez.com",
        role="admin",
        name=f"Gestor Demo {i}",
        nif=nif_livre(910000000 + i),
    )

    admins.append(admin)


# ============================================================
# CLIENTES
# ============================================================

print("A criar clientes...")

clientes = []

for i in range(1, TOTAL_CLIENTES + 1):
    cliente = criar_client(
        username=f"cliente_demo_{i}",
        email=f"cliente_demo_{i}@hermez.com",
        name=f"Cliente Demo {i}",
        nif=nif_livre(920000000 + i),
        genero="M" if i % 2 else "F",
    )

    if hasattr(cliente, "telefone"):
        cliente.telefone = f"96{i:07d}"[-9:]
        cliente.save()

    clientes.append(cliente)


# ============================================================
# MOTORISTAS
# ============================================================

print("A criar motoristas...")

motoristas = []

for i in range(1, TOTAL_MOTORISTAS + 1):
    motorista = criar_driver(
        username=f"motorista_demo_{i}",
        email=f"motorista_demo_{i}@hermez.com",
        name=f"Motorista Demo {i}",
        nif=nif_livre(930000000 + i),
        i=i,
    )

    motoristas.append(motorista)


# ============================================================
# TÁXIS
# ============================================================

taxis = []

if Taxi:
    print("A criar táxis...")

    marcas_modelos = [
        ("Toyota", "Prius", "Combustão", "Básico"),
        ("Toyota", "Corolla", "Combustão", "Básico"),
        ("Hyundai", "Ioniq", "Elétrico", "Básico"),
        ("Kia", "Niro", "Elétrico", "Básico"),
        ("Mercedes-Benz", "E-Class", "Combustão", "Luxuoso"),
        ("BMW", "5 Series", "Combustão", "Luxuoso"),
        ("Volkswagen", "Passat", "Combustão", "Básico"),
        ("Renault", "Megane", "Combustão", "Básico"),
        ("Peugeot", "308", "Combustão", "Básico"),
        ("Nissan", "Qashqai", "Combustão", "Luxuoso"),
    ]

    for i in range(1, TOTAL_TAXIS + 1):
        marca, modelo, motor, conforto = marcas_modelos[i - 1]

        matricula = f"AA-{i:02d}-DD"

        taxi, created = criar_objeto(
            Taxi,
            matricula=matricula,
            defaults={
                "marca": marca,
                "modelo": modelo,
                "ano_compra": 2018 + (i % 7),
                "consumo_medio": Decimal("6.50") if motor != "Elétrico" else Decimal("0.10"),
                "tipo_motor": motor,
                "nivel_conforto": conforto,
                "estado": "disponivel",
                "observacoes": "Táxi criado para dados de demonstração.",
                "latitude": Decimal("38.756734"),
                "longitude": Decimal("-9.155412"),
            },
        )

        taxis.append(taxi)
else:
    print("Modelo Taxi não encontrado. A saltar criação de táxis.")


# ============================================================
# TURNOS FUTUROS
# ============================================================

if Shift and taxis and motoristas:
    print("A criar turnos de demonstração...")

    for i in range(1, TOTAL_TURNOS_FUTUROS + 1):
        inicio = timezone.now() + timedelta(days=i, hours=1)
        inicio = inicio.replace(second=0, microsecond=0)

        fim = inicio + timedelta(hours=4)

        driver = motoristas[i % len(motoristas)]
        taxi = taxis[i % len(taxis)]

        data = {
            "driver": driver,
            "taxi": taxi,
            "driver_id": getattr(driver, "id", None),
            "taxi_id": getattr(taxi, "id", None),
            "start_date": inicio,
            "end_date": fim,
            "status_shift": "active",
        }

        lookup = {
            "driver_id": getattr(driver, "id", None),
            "taxi_id": getattr(taxi, "id", None),
            "start_date": inicio,
        }

        Shift.objects.get_or_create(
            **filtrar_campos(Shift, lookup),
            defaults=filtrar_campos(Shift, data),
        )
else:
    print("Modelo Shift não encontrado ou sem táxis/motoristas. A saltar turnos.")


# ============================================================
# VIAGENS
# ============================================================

viagens = []

if Trip and clientes and motoristas and taxis:
    print("A criar viagens...")

    locais = [
        ("Aeroporto", "Telheiras"),
        ("Benfica", "Oriente"),
        ("Saldanha", "Campo Grande"),
        ("Marquês de Pombal", "Cais do Sodré"),
        ("Alvalade", "Belém"),
        ("Odivelas", "Baixa-Chiado"),
        ("Amadora", "Entrecampos"),
        ("Parque das Nações", "Sete Rios"),
        ("Lumiar", "Areeiro"),
        ("Restauradores", "Alameda"),
    ]

    base_data = timezone.now().replace(hour=12, minute=0, second=0, microsecond=0)

    for i in range(1, TOTAL_VIAGENS + 1):
        origem, destino = locais[(i - 1) % len(locais)]

        inicio = base_data - timedelta(days=i)
        fim = inicio + timedelta(minutes=20 + i)

        preco = Decimal("5.00") + Decimal(str(i * 1.15))
        kms = Decimal("3.00") + Decimal(str(i * 0.7))

        cliente = clientes[i % len(clientes)]
        motorista = motoristas[i % len(motoristas)]
        taxi = taxis[i % len(taxis)]

        lookup = {
            "start_location": origem,
            "end_location": destino,
            "start_date": inicio,
        }

        trip = Trip.objects.filter(**filtrar_campos(Trip, lookup)).first()

        if not trip:
            data = {
                "client": cliente,
                "driver": motorista,
                "taxi": taxi,
                "client_id": getattr(cliente, "id", None),
                "driver_id": getattr(motorista, "id", None),
                "taxi_id": getattr(taxi, "id", None),
                "start_location": origem,
                "end_location": destino,
                "n_people": (i % 4) + 1,
                "n_kms": kms,
                "price": preco,
                "status_trip": "finished",
                "payment_status": "paid",
                "start_date": inicio,
                "end_date": fim,
                "nivel_conforto": "Luxuoso" if i % 4 == 0 else "Básico",
            }

            trip = Trip.objects.create(**filtrar_campos(Trip, data))

        viagens.append(trip)
else:
    print("Modelo Trip não encontrado ou faltam clientes/motoristas/táxis. A saltar viagens.")


# ============================================================
# FATURAS
# ============================================================

if Invoice and viagens:
    print("A criar faturas...")

    ano = timezone.now().year

    ultimo_numero = (
        Invoice.objects
        .filter(ano=ano)
        .aggregate(maior=Max("n_fatura"))
        .get("maior")
        or 0
    )

    proximo_numero = ultimo_numero + 1

    for trip in viagens[:TOTAL_FATURAS]:
        if Invoice.objects.filter(trip=trip).exists():
            continue

        valor_viagem = getattr(trip, "price", Decimal("10.00"))

        data = {
            "trip": trip,
            "n_fatura": proximo_numero,
            "ano": ano,
            "data": timezone.now() - timedelta(days=max(0, TOTAL_FATURAS - proximo_numero)),
            "valor": valor_viagem,
            "price": valor_viagem,
        }

        Invoice.objects.create(**filtrar_campos(Invoice, data))

        proximo_numero += 1
else:
    print("Modelo Invoice não encontrado ou sem viagens. A saltar faturas.")


# ============================================================
# REABASTECIMENTOS
# ============================================================

if Refuel and taxis and motoristas and Shift:
    print("A criar reabastecimentos...")

    base_data = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0)

    for i in range(1, TOTAL_REABASTECIMENTOS + 1):
        taxi = taxis[i % len(taxis)]
        motorista = motoristas[i % len(motoristas)]

        data_inicio = base_data - timedelta(days=i)
        data_fim = data_inicio + timedelta(minutes=10)

        shift_inicio = data_inicio - timedelta(minutes=30)
        shift_fim = data_fim + timedelta(hours=3)

        shift_data = {
            "driver": motorista,
            "taxi": taxi,
            "driver_id": getattr(motorista, "id", None),
            "taxi_id": getattr(taxi, "id", None),
            "start_date": shift_inicio,
            "end_date": shift_fim,
            "status_shift": "inactive",
        }

        shift_lookup = {
            "driver_id": getattr(motorista, "id", None),
            "taxi_id": getattr(taxi, "id", None),
            "start_date": shift_inicio,
        }

        shift, _ = Shift.objects.get_or_create(
            **filtrar_campos(Shift, shift_lookup),
            defaults=filtrar_campos(Shift, shift_data),
        )

        tipo_motor = str(getattr(taxi, "tipo_motor", "")).lower()
        is_eletrico = "eletr" in tipo_motor or "elétr" in tipo_motor

        data = {
            "shift": shift,
            "shift_id": getattr(shift, "id", None),
            "taxi": taxi,
            "taxi_id": getattr(taxi, "id", None),
            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "litros": Decimal("0.00") if is_eletrico else Decimal("35.50"),
            "kwh": Decimal("45.00") if is_eletrico else Decimal("0.00"),
            "euros_pagos": Decimal("65.00") + Decimal(i),
            "kms_taxi": Decimal("10000") + Decimal(i * 250),
            "tipo": "eletrico" if is_eletrico else "gasolina",
        }

        lookup = {
            "shift_id": getattr(shift, "id", None),
            "data_inicio": data_inicio,
        }

        Refuel.objects.get_or_create(
            **filtrar_campos(Refuel, lookup),
            defaults=filtrar_campos(Refuel, data),
        )

elif Refuel and taxis:
    print("Modelo Shift não encontrado. A saltar reabastecimentos porque Refuel exige shift.")
else:
    print("Modelo Refuel não encontrado ou sem táxis. A saltar reabastecimentos.")


# ============================================================
# CONTAGEM FINAL
# ============================================================

print("\nDados de demonstração criados/confirmados com sucesso.\n")

print(f"Users: {User.objects.count()}")

if Client:
    print(f"Clientes: {Client.objects.count()}")

if Driver:
    print(f"Motoristas: {Driver.objects.count()}")

if Taxi:
    print(f"Táxis: {Taxi.objects.count()}")

if Trip:
    print(f"Viagens: {Trip.objects.count()}")

if Invoice:
    print(f"Faturas: {Invoice.objects.count()}")

if Shift:
    print(f"Turnos: {Shift.objects.count()}")

if Refuel:
    print(f"Reabastecimentos: {Refuel.objects.count()}")