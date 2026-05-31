from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from django.conf import settings
from django.db import IntegrityError, transaction

from apps.user.models import User

from .models import Client


def create_client(data):
    username = data['username'].strip()
    email = data['email'].strip()
    password = data['password']
    name = data['name'].strip()
    nif = str(data['nif']).strip()
    genero = data['genero'].strip().lower()

    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    try:
        with transaction.atomic():
            if User.objects.filter(username=username).exists():
                return None, 'Username ja existe.', 409
            if User.objects.filter(email=email).exists():
                return None, 'Email ja registado.', 409
            if User.objects.filter(nif=nif).exists():
                return None, 'NIF ja registado.', 409

            client = Client.objects.create(
                username=username,
                email=email,
                password=hashed,
                name=name,
                role='cliente',
                nif=nif,
                genero=genero,
            )
    except IntegrityError:
        return None, 'Dados duplicados.', 409

    return client, None, None


def login_client(data):
    nif = str(data.get('nif', '')).strip()
    password = data.get('password', '')

    if not password:
        return None, 'password e obrigatoria.', 400

    try:
        user = User.objects.get(nif=nif, role='cliente')
    except User.DoesNotExist:
        return None, 'Credenciais invalidas', 401

    stored_hash = user.password or ''
    if not stored_hash:
        return None, 'Credenciais invalidas', 401

    try:
        if not bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
            return None, 'Credenciais invalidas', 401
    except Exception:
        return None, 'Credenciais invalidas', 401

    now = datetime.now(tz=timezone.utc)
    expiry = now + timedelta(hours=settings.JWT_EXPIRY_HOURS)
    payload = {
        'id': str(user.id),
        'nif': user.nif,
        'role': user.role,
        'iat': int(now.timestamp()),
        'exp': int(expiry.timestamp()),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm='HS256')

    return {'token': token, 'role': user.role, 'nome': user.name}, None, None