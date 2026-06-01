import re
import secrets
from datetime import date, datetime, timezone, timedelta
import logging

import bcrypt
import jwt
import requests
import csv
from pathlib import Path
from django.conf import settings
from django.db import IntegrityError, transaction
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.shift.models import Shift

from apps.user.models import User
from apps.user.utils import validar_nif
from .models import Driver
from .validators import validate_driver_registration_payload

logger = logging.getLogger(__name__)



def motorista_para_json(motorista):
    return {
        'id': str(motorista.id),
        'username': motorista.username,
        'email': motorista.email,
        'nome': motorista.name,
        'role': motorista.role,
        'nif': motorista.nif,
        'telefone': motorista.mobile or '',
        'ano_nascimento': motorista.ano_nascimento,
        'genero': motorista.genero,
        'n_carta': motorista.num_carta_conducao,
        'validade_carta': str(motorista.validade_carta) if motorista.validade_carta else '',
        'localidade': motorista.localidade,
        'codigo_postal': motorista.codigo_postal,
        'estado': motorista.estado,
    }

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CP_RE = re.compile(r'^\d{4}-\d{3}$')


_CP_RE = re.compile(r'^\d{4}-\d{3}$')


def _lookup_localidade(codigo_postal: str):
    """
    Procura a localidade num ficheiro CSV local de códigos postais.
    O ficheiro tem cabeçalho com colunas:
    num_cod_postal, ext_cod_postal, desig_postal
    """
    logger.debug(f"_lookup_localidade called with: {codigo_postal}")

    if not _CP_RE.match(codigo_postal):
        return None, Response(
            {'message': 'Formato de código postal inválido. Use XXXX-XXX.'},
            status=400,
        )

    base_dir = Path(__file__).resolve().parents[3]
    csv_path = base_dir / 'data' / 'codigos_postais.csv'
    logger.debug(f"A procurar ficheiro CSV em: {csv_path}")

    if not csv_path.exists():
        return None, Response(
            {'message': 'Base de dados de códigos postais não encontrada no servidor.'},
            status=500,
        )

    try:
        with open(csv_path, mode='r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)

            for row in reader:
                cp4 = str(row.get('num_cod_postal', '')).strip()
                cp3 = str(row.get('ext_cod_postal', '')).strip()
                localidade = str(row.get('desig_postal', '')).strip()

                if not cp4 or not cp3:
                    continue

                cp = f"{cp4}-{cp3.zfill(3)}"

                if cp == codigo_postal and localidade:
                    logger.debug(f"Localidade encontrada: {localidade}")
                    return localidade, None

    except Exception as e:
        logger.error(f"Erro ao ler CSV de códigos postais: {e}")
        return None, Response(
            {'message': 'Erro ao ler a base de códigos postais.'},
            status=500,
        )

    logger.debug(f"Código postal não encontrado no CSV: {codigo_postal}")
    return None, Response(
        {'message': 'Código postal não encontrado.'},
        status=400,
    )


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

def _validate_validade_carta(validade_raw):
    """
    Valida a validade da carta de condução.
    A carta não pode estar expirada e não pode ter validade superior a 15 anos no futuro.
    """
    if not validade_raw:
        return None, Response(
            {'message': 'validade_carta é obrigatória.'},
            status=400,
        )

    try:
        validade = datetime.strptime(str(validade_raw), '%Y-%m-%d').date()
    except ValueError:
        return None, Response(
            {'message': 'validade_carta inválida. Use YYYY-MM-DD.'},
            status=400,
        )

    hoje = date.today()
    limite_maximo = hoje.replace(year=hoje.year + 15)

    if validade < hoje:
        return None, Response(
            {'message': 'A carta de condução está expirada.'},
            status=400,
        )

    if validade > limite_maximo:
        return None, Response(
            {'message': 'A validade da carta não pode ser superior a 15 anos no futuro.'},
            status=400,
        )

    return validade, None


# ---------------------------------------------------------------------------
# GET /motorista/localidade/<codigo_postal>/
# Endpoint para lookup de localidade (auto-preenchimento do formulário)
# ---------------------------------------------------------------------------

@api_view(['GET'])
def get_localidade(request, codigo_postal):
    """
    Retorna a localidade para um código postal válido.
    Formato esperado: XXXX-XXX (ex: 1234-567)
    """
    logger.debug(f"get_localidade called with codigo_postal: {codigo_postal}")
    localidade, err = _lookup_localidade(codigo_postal)
    if err:
        logger.debug(f"Error from _lookup_localidade: {err}")
        return err
    
    logger.debug(f"Localidade found: {localidade}")
    return Response(
        {'localidade': localidade},
        status=200,
    )


# ---------------------------------------------------------------------------
# View
# ---------------------------------------------------------------------------

@api_view(['POST'])
def registo_motorista(request):
    data = request.data

    # --- Validar payload ---
    err = validate_driver_registration_payload(data)
    if err:
        return Response({'message': err}, status=400)

    # Aceita tanto os nomes do frontend como os do backend
    email     = str(data.get('email', '')).strip()
    name      = str(data.get('nome') or data.get('name', '')).strip()
    nif       = str(data.get('nif', '')).strip()
    genero    = str(data.get('genero', '')).strip().capitalize()
    num_carta = str(data.get('n_carta') or data.get('num_carta_conducao', '')).strip()
    telefone  = str(data.get('telefone') or data.get('mobile', '')).strip()
    validade_carta_raw = data.get('validade_carta', '') or ''
    codigo_postal = str(data.get('codigo_postal', '')).strip()

    # username auto-gerado a partir do email se não fornecido
    username = str(data.get('username') or email.split('@')[0]).strip()

    # data_nascimento (YYYY-MM-DD) → ano_nascimento
    data_nasc_raw = data.get('data_nascimento') or data.get('ano_nascimento', '')

    # --- Validações básicas ---
    if not email or not name or not nif or not genero or not num_carta:
        return Response(
            {'message': 'Campos obrigatórios em falta: email, nome, nif, genero, n_carta'},
            status=400,
        )

    # --- Extrair ano de nascimento ---
    if isinstance(data_nasc_raw, str) and '-' in data_nasc_raw:
        try:
            ano_nascimento_raw = int(data_nasc_raw.split('-')[0])
        except ValueError:
            return Response({'message': 'data_nascimento inválida.'}, status=400)
    else:
        ano_nascimento_raw = data_nasc_raw

    ano_nascimento, err = _validate_ano_nascimento(ano_nascimento_raw)
    if err:
        return err

    # --- Validate genero ---
    if genero in ('Masculino', 'M'):
        genero_db = 'M'
    elif genero in ('Feminino', 'F'):
        genero_db = 'F'
    else:
        return Response({'message': "Género inválido."}, status=400)

    # --- Validate num_carta ---
    if not num_carta or len(num_carta) < 5:
        return Response({'message': 'n_carta deve ter pelo menos 5 caracteres.'}, status=400)

    # --- Validade da carta ---
    validade_carta, err = _validate_validade_carta(validade_carta_raw)
    if err:
        return err

    # --- Lookup localidade (opcional, mas se vier tem de ser válida) ---
    localidade = ''
    if codigo_postal:
        localidade, err = _lookup_localidade(codigo_postal)
        if err:
            return err

    # --- Password aleatória (autenticação via Firebase) ---
    password = data.get('password') or secrets.token_urlsafe(16)
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # --- Atomic creation with uniqueness checks inside the transaction.
    #     This eliminates the race-condition window that exists when the
    #     checks run outside of atomic() — two concurrent requests could
    #     both pass the pre-checks and then one would hit a DB-level
    #     UNIQUE constraint, producing an IntegrityError that we now
    #     catch explicitly instead of returning a generic 500. ---
    try:
        with transaction.atomic():
            if User.objects.filter(username=username).exists():
                return Response({'message': 'Username já existe.'}, status=409)
            if User.objects.filter(email=email).exists():
                return Response({'message': 'Email já registado.'}, status=409)
            if User.objects.filter(nif=nif).exists():
                return Response({'message': 'NIF já registado.'}, status=409)
            if Driver.objects.filter(num_carta_conducao=num_carta).exists():
                return Response(
                    {'message': 'Número de carta de condução já registado.'},
                    status=409,
                )

            motorista = Driver.objects.create(
                username=username,
                email=email,
                password=hashed,
                name=name,
                role='motorista',
                nif=nif,
                mobile=telefone,
                ano_nascimento=ano_nascimento,
                genero=genero_db,
                num_carta_conducao=num_carta,
                validade_carta=validade_carta,
                localidade=localidade,
                codigo_postal=codigo_postal,
            )
    except IntegrityError as e:
        return Response(
            {'message': f'Dados duplicados: {e}'},
            status=409,
        )
    except Exception:
        return Response(
            {'message': 'Erro interno ao criar o registo. Tente novamente.'},
            status=500,
        )

    return Response({'success': True, 'motorista': motorista_para_json(motorista)}, status=201)


# ---------------------------------------------------------------------------
# POST /auth/login  (Auth04)
# ---------------------------------------------------------------------------

_INVALID_CREDENTIALS = {'message': 'Credenciais inválidas'}


@api_view(['POST'])
def login_nif(request):
    data = request.data

    nif      = str(data.get('nif', '')).strip()
    password = data.get('password', '')

    # --- NIF format + mod-11 check (no DB hit on failure) ---
    if not validar_nif(nif):
        return Response({'message': 'NIF inválido.'}, status=400)

    if not password:
        return Response({'message': 'password é obrigatória.'}, status=400)

    # --- Lookup user by NIF ---
    try:
        user = User.objects.get(nif=nif)
    except User.DoesNotExist:
        return Response(_INVALID_CREDENTIALS, status=401)

    # --- Verify password with bcrypt ---
    stored_hash = user.password or ''
    if not stored_hash:
        return Response(_INVALID_CREDENTIALS, status=401)

    try:
        match = bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
    except Exception:
        return Response(_INVALID_CREDENTIALS, status=401)

    if not match:
        return Response(_INVALID_CREDENTIALS, status=401)

    # --- Generate JWT ---
    now = datetime.now(tz=timezone.utc)
    expiry = now + timedelta(hours=settings.JWT_EXPIRY_HOURS)

    payload = {
        'id':   str(user.id),
        'nif':  user.nif,
        'role': user.role,
        'iat':  int(now.timestamp()),
        'exp':  int(expiry.timestamp()),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm='HS256')

    return Response(
        {
            'token': token,
            'role':  user.role,
            'nome':  user.name,
        },
        status=200,
    )


@api_view(['GET'])
def listar_motoristas(request):
    motoristas = Driver.objects.all().order_by('-updated_at')

    resultado = []
    for motorista in motoristas:
        resultado.append(motorista_para_json(motorista))

    return Response(
        {
            'success': True,
            'motoristas': resultado,
            'total': len(resultado),
        },
        status=200,
    )


@api_view(['GET', 'PATCH', 'PUT', 'DELETE'])
def gerir_motorista(request, id_motorista):
    motorista = Driver.objects.filter(pk=id_motorista).first()

    if not motorista:
        return Response({'message': 'Motorista nao encontrado.'}, status=404)

    if request.method == 'GET':
        return Response(
            {
                'success': True,
                'motorista': motorista_para_json(motorista),
            },
            status=200,
        )

    if request.method == 'DELETE':
        tem_turnos = Shift.objects.filter(driver_id=motorista.id).exists()

        if tem_turnos:
            return Response(
                {
                    'message': 'Não é possível remover o motorista porque já requisitou um táxi para um turno.'
                },
                status=409,
            )

        motorista_id = str(motorista.id)
        motorista.delete()

        return Response(
            {
                'success': True,
                'message': 'Motorista apagado.',
                'id': motorista_id,
            },
            status=200,
        )

    data = request.data

    if not data:
        return Response({'message': 'Nenhum campo para atualizar.'}, status=400)
    
    novo_estado = None

    if 'username' in data:
        username = str(data['username']).strip()
        if not username:
            return Response({'message': 'username e obrigatorio.'}, status=400)
        if User.objects.filter(username=username).exclude(pk=motorista.pk).exists():
            return Response({'message': 'Username ja existe.'}, status=409)
        motorista.username = username

    if 'email' in data:
        email = str(data['email']).strip()
        if not email:
            return Response({'message': 'email e obrigatorio.'}, status=400)
        if User.objects.filter(email=email).exclude(pk=motorista.pk).exists():
            return Response({'message': 'Email ja registado.'}, status=409)
        motorista.email = email

    # aceita 'nome' (frontend) ou 'name' (backend)
    name_val = data.get('nome') or data.get('name')
    if name_val is not None:
        name_val = str(name_val).strip()
        if not name_val:
            return Response({'message': 'nome e obrigatorio.'}, status=400)
        motorista.name = name_val

    if 'nif' in data:
        nif = str(data['nif']).strip()
        if not re.fullmatch(r'^[123456789]\d{8}$', nif):
            return Response({'message': 'NIF invalido.'}, status=400)
        if User.objects.filter(nif=nif).exclude(pk=motorista.pk).exists():
            return Response({'message': 'NIF ja registado.'}, status=409)
        motorista.nif = nif

    if 'telefone' in data:
        motorista.mobile = str(data['telefone']).strip()

    # aceita 'data_nascimento' (frontend) ou 'ano_nascimento' (backend)
    nasc_val = data.get('data_nascimento') or data.get('ano_nascimento')
    if nasc_val is not None:
        if isinstance(nasc_val, str) and '-' in nasc_val:
            try:
                nasc_val = int(nasc_val.split('-')[0])
            except ValueError:
                return Response({'message': 'data_nascimento invalida.'}, status=400)
        ano_nascimento, err = _validate_ano_nascimento(nasc_val)
        if err:
            return err
        motorista.ano_nascimento = ano_nascimento

    if 'genero' in data:
        genero = str(data['genero']).strip()
        genero = {'O': 'Outro'}.get(genero, genero)
        if genero not in ('M', 'F', 'Outro'):
            return Response({'message': "genero deve ser 'M', 'F' ou 'Outro'."}, status=400)
        motorista.genero = genero

    # aceita 'n_carta' (frontend) ou 'num_carta_conducao' (backend)
    carta_val = data.get('n_carta') or data.get('num_carta_conducao')
    if carta_val is not None:
        num_carta = str(carta_val).strip()
        if len(num_carta) < 5:
            return Response({'message': 'n_carta deve ter pelo menos 5 caracteres.'}, status=400)
        if Driver.objects.filter(num_carta_conducao=num_carta).exclude(pk=motorista.pk).exists():
            return Response({'message': 'Numero de carta de conducao ja registado.'}, status=409)
        motorista.num_carta_conducao = num_carta

    if 'validade_carta' in data:
        validade_carta, err = _validate_validade_carta(data['validade_carta'])
        if err:
            return err

        motorista.validade_carta = validade_carta

    if 'codigo_postal' in data:
        codigo_postal = str(data['codigo_postal']).strip()
        localidade, err = _lookup_localidade(codigo_postal)
        if err:
            return err
        motorista.codigo_postal = codigo_postal
        motorista.localidade = localidade

    if 'estado' in data:
        estado = str(data['estado']).strip()
        if estado not in ('disponivel', 'indisponivel'):
            return Response(
                {'message': "estado deve ser 'disponivel' ou 'indisponivel'."},
                status=400,
            )
        motorista.estado = estado
        novo_estado = estado

    try:
        motorista.save()

        if novo_estado is not None:
            Driver.objects.filter(pk=motorista.pk).update(estado=novo_estado)
            motorista.refresh_from_db()

    except IntegrityError:
        return Response({'message': 'Erro ao atualizar motorista.'}, status=409)
    
    return Response(
        {
            'success': True,
            'motorista': motorista_para_json(motorista),
        },
        status=200,
    )


@api_view(['PATCH'])
def atualizar_estado(request, id_motorista):
    """
    PATCH /api/motoristas/<id>/estado/
    Body: { "estado": "disponivel" | "indisponivel" }
    """
    motorista = Driver.objects.filter(pk=id_motorista).first()
    if not motorista:
        return Response({'message': 'Motorista não encontrado.'}, status=404)

    estado = request.data.get('estado', '').strip()
    if estado not in ('disponivel', 'indisponivel'):
        return Response(
            {'message': "estado deve ser 'disponivel' ou 'indisponivel'."},
            status=400,
        )

    motorista.estado = estado
    motorista.save(update_fields=['estado'])

    return Response(
            {
                'success': True,
                'motorista': motorista_para_json(motorista),
            },
            status=200,
        )