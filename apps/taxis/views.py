import re
from datetime import date

import bcrypt
import requests
from django.conf import settings
from django.db import transaction
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.users.models import User
from .models import Motorista


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CP_RE = re.compile(r'^\d{4}-\d{3}$')


def _lookup_localidade(codigo_postal: str):
    """
    Consulta a API de códigos postais e devolve a localidade.
    Retorna (localidade: str, error_response | None).
    """
    if not _CP_RE.match(codigo_postal):
        return None, Response(
            {'message': 'Formato de código postal inválido. Use XXXX-XXX.'},
            status=400,
        )

    cp4, cp3 = codigo_postal.split('-')
    url = f"{settings.POSTAL_CODE_API_URL}/{cp4}/{cp3}"

    try:
        resp = requests.get(url, timeout=5)
    except requests.RequestException:
        return None, Response(
            {'message': 'Serviço de códigos postais indisponível.'},
            status=502,
        )

    if resp.status_code != 200:
        return None, Response(
            {'message': 'Código postal não encontrado.'},
            status=400,
        )

    try:
        data = resp.json()
    except ValueError:
        return None, Response(
            {'message': 'Resposta inválida do serviço de códigos postais.'},
            status=502,
        )

    if not data:
        return None, Response(
            {'message': 'Código postal não encontrado.'},
            status=400,
        )

    localidade = data[0].get('Localidade', '').strip()
    if not localidade:
        return None, Response(
            {'message': 'Código postal não encontrado.'},
            status=400,
        )

    return localidade, None


def _validate_ano_nascimento(ano):
    """Valida que o condutor tem pelo menos 18 anos e nasceu depois de 1900."""
    try:
        ano = int(ano)
    except (TypeError, ValueError):
        return None, Response(
            {'message': 'ano_nascimento deve ser um número inteiro.'},
            status=400,
        )

    ano_atual = date.today().year
    if ano < 1900:
        return None, Response(
            {'message': 'ano_nascimento deve ser posterior a 1900.'},
            status=400,
        )
    if ano_atual - ano < 18:
        return None, Response(
            {'message': 'O condutor deve ter pelo menos 18 anos.'},
            status=400,
        )
    return ano, None


def _validate_num_carta(num_carta: str):
    """Alfanumérico, mínimo 5 caracteres."""
    if not num_carta or len(num_carta) < 5:
        return Response(
            {'message': 'num_carta_conducao deve ter pelo menos 5 caracteres.'},
            status=400,
        )
    if not re.match(r'^[A-Za-z0-9]+$', num_carta):
        return Response(
            {'message': 'num_carta_conducao deve ser alfanumérico.'},
            status=400,
        )
    return None


# ---------------------------------------------------------------------------
# View
# ---------------------------------------------------------------------------

@api_view(['POST'])
def registo_motorista(request):
    data = request.data

    # --- Required field presence ---
    required = ('username', 'email', 'password', 'name',
                 'ano_nascimento', 'genero', 'num_carta_conducao', 'codigo_postal')
    missing = [f for f in required if not data.get(f)]
    if missing:
        return Response(
            {'message': f"Campos obrigatórios em falta: {', '.join(missing)}"},
            status=400,
        )

    username         = data['username'].strip()
    email            = data['email'].strip()
    password         = data['password']
    name             = data['name'].strip()
    genero           = data['genero']
    num_carta        = data['num_carta_conducao'].strip()
    codigo_postal    = data['codigo_postal'].strip()

    # --- Validate ano_nascimento ---
    ano_nascimento, err = _validate_ano_nascimento(data['ano_nascimento'])
    if err:
        return err

    # --- Validate genero ---
    if genero not in ('M', 'F', 'Outro'):
        return Response(
            {'message': "genero deve ser 'M', 'F' ou 'Outro'."},
            status=400,
        )

    # --- Validate num_carta_conducao ---
    err = _validate_num_carta(num_carta)
    if err:
        return err

    # --- Lookup localidade via postal code API (before DB writes) ---
    localidade, err = _lookup_localidade(codigo_postal)
    if err:
        return err

    # --- Uniqueness checks ---
    if User.objects.filter(username=username).exists():
        return Response({'message': 'Username já existe.'}, status=409)
    if User.objects.filter(email=email).exists():
        return Response({'message': 'Email já registado.'}, status=409)
    if Motorista.objects.filter(num_carta_conducao=num_carta).exists():
        return Response(
            {'message': 'Número de carta de condução já registado.'},
            status=409,
        )

    # --- Hash password ---
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # --- Atomic creation: rollback both records if anything fails ---
    try:
        with transaction.atomic():
            user = User.objects.create(
                username=username,
                email=email,
                password=hashed,
                name=name,
                role='motorista',
            )
            motorista = Motorista.objects.create(
                user=user,
                ano_nascimento=ano_nascimento,
                genero=genero,
                num_carta_conducao=num_carta,
                localidade=localidade,
                codigo_postal=codigo_postal,
            )
    except Exception:
        return Response(
            {'message': 'Erro interno ao criar o registo. Tente novamente.'},
            status=500,
        )

    return Response(
        {
            'success': True,
            'user': {
                'id':                  str(user.id),
                'username':            user.username,
                'email':               user.email,
                'name':                user.name,
                'role':                user.role,
                'ano_nascimento':      motorista.ano_nascimento,
                'genero':              motorista.genero,
                'num_carta_conducao':  motorista.num_carta_conducao,
                'localidade':          motorista.localidade,
                'codigo_postal':       motorista.codigo_postal,
            },
        },
        status=201,
    )
