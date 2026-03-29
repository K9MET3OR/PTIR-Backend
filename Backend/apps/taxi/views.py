from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from math import atan2, cos, radians, sin, sqrt
from uuid import UUID

from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Taxi

_NIVEL_CANON = {
    'standard': 'Standard',
    'conforto': 'Conforto',
    'premium': 'Premium',
}
_MOTOR_CANON = {
    'gasolina': 'Gasolina',
    'diesel': 'Diesel',
    'elétrico': 'Elétrico',
    'híbrido': 'Híbrido',
}
_NIVEL_VALIDOS = frozenset(_NIVEL_CANON.keys())
_MOTOR_VALIDOS = frozenset(_MOTOR_CANON.keys())
_TAXI_UPDATE_FIELDS = frozenset(('modelo', 'matricula', 'ano_compra', 'consumo_medio', 'marca', 'tipo_motor', 'nivel_conforto'))

# ---------------------------------------------------------------------------
# Helpers — serialização
# ---------------------------------------------------------------------------


def _taxi_to_dict(taxi: Taxi) -> dict:
    tipo_motor_raw = str(taxi.tipo_motor or '').strip()
    nivel_raw = str(taxi.nivel_conforto or '').strip()
    tipo_motor = _MOTOR_CANON.get(tipo_motor_raw.lower(), tipo_motor_raw)
    nivel_conforto = _NIVEL_CANON.get(nivel_raw.lower(), nivel_raw)

    return {
        'id': str(taxi.id),
        'id_taxi': str(taxi.id),
        'modelo': taxi.modelo,
        'matricula': taxi.matricula,
        'ano_compra': taxi.ano_compra,
        'consumo_medio': float(taxi.consumo_medio),
        'marca': taxi.marca or '',
        'tipo_motor': tipo_motor,
        'nivel_conforto': nivel_conforto,
        'created_at': taxi.created_at.isoformat() if taxi.created_at else None,
        'updated_at': taxi.updated_at.isoformat() if taxi.updated_at else None,
    }


# ---------------------------------------------------------------------------
# Helpers — validação (criação)
# ---------------------------------------------------------------------------


def _parse_ano_compra(raw):
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _parse_consumo_medio(raw):
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if value <= 0:
        return None
    return value


def _parse_coordinate(raw, name):
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None, f"{name} deve ser um numero valido."
    return value, None


def _haversine_km(lat1, lon1, lat2, lon2):
    # Distancia geodesica aproximada (km) entre dois pontos GPS.
    earth_radius_km = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return earth_radius_km * c


def validate_taxi_payload(data):
    """
    Valida o corpo para POST / registo.
    Devolve mensagem de erro ou None se estiver correto.
    """
    required = ('modelo', 'matricula', 'ano_compra', 'consumo_medio')
    missing = []
    for field in required:
        if field not in data:
            missing.append(field)
            continue
        value = data.get(field)
        if value in (None, ''):
            missing.append(field)
    if missing:
        return f"Campos obrigatorios em falta: {', '.join(missing)}"

    modelo = str(data.get('modelo', '')).strip()
    if len(modelo) < 2:
        return 'modelo deve ter pelo menos 2 caracteres.'

    matricula = str(data.get('matricula', '')).strip().upper()
    if len(matricula) < 5:
        return 'matricula invalida.'

    ano = _parse_ano_compra(data.get('ano_compra'))
    if ano is None:
        return 'ano_compra deve ser um numero inteiro.'

    ano_atual = date.today().year
    if ano < 1980 or ano > ano_atual:
        return f'ano_compra deve estar entre 1980 e {ano_atual}.'

    consumo = _parse_consumo_medio(data.get('consumo_medio'))
    if consumo is None:
        return 'consumo_medio deve ser um numero maior que 0.'

    if 'marca' in data and data.get('marca') not in (None, ''):
        marca = str(data['marca']).strip()
        if len(marca) > 50:
            return 'marca demasiado longa.'

    if 'tipo_motor' in data and data.get('tipo_motor') not in (None, ''):
        tm = str(data['tipo_motor']).strip().lower()
        if tm not in _MOTOR_VALIDOS:
            return "tipo_motor deve ser 'Gasolina', 'Diesel', 'Elétrico' ou 'Híbrido'."

    if 'nivel_conforto' in data and data.get('nivel_conforto') not in (None, ''):
        nv = str(data['nivel_conforto']).strip().lower()
        if nv not in _NIVEL_VALIDOS:
            return "nivel_conforto deve ser 'Standard', 'Conforto' ou 'Premium'."

    return None


def _normalize_create_body(data):
    err = validate_taxi_payload(data)
    if err:
        return None, err

    marca = str(data.get('marca', '')).strip() if data.get('marca') is not None else ''
    motor = (str(data.get('tipo_motor', 'gasolina')).strip().lower()
             if data.get('tipo_motor') not in (None, '') else 'gasolina')
    if motor not in _MOTOR_VALIDOS:
        motor = 'gasolina'
    nivel = (str(data.get('nivel_conforto', 'conforto')).strip().lower()
             if data.get('nivel_conforto') not in (None, '') else 'conforto')
    if nivel not in _NIVEL_VALIDOS:
        nivel = 'conforto'

    return {
        'modelo': str(data['modelo']).strip(),
        'matricula': str(data['matricula']).strip().upper(),
        'ano_compra': int(data['ano_compra']),
        'consumo_medio': _parse_consumo_medio(data['consumo_medio']),
        'marca': marca[:50],
        'tipo_motor': _MOTOR_CANON.get(motor, 'Gasolina'),
        'nivel_conforto': _NIVEL_CANON.get(nivel, 'Conforto'),
    }, None


# ---------------------------------------------------------------------------
# Helpers — validação (atualização parcial)
# ---------------------------------------------------------------------------


def validate_taxi_update_payload(data):
    """Valida apenas os campos enviados num PATCH/PUT."""
    if not data:
        return 'Nenhum campo para atualizar.'

    if not _TAXI_UPDATE_FIELDS.intersection(data.keys()):
        return 'Nenhum campo para atualizar.'

    if 'modelo' in data:
        modelo = str(data['modelo']).strip()
        if len(modelo) < 2:
            return 'modelo deve ter pelo menos 2 caracteres.'

    if 'matricula' in data:
        matricula = str(data['matricula']).strip().upper()
        if len(matricula) < 5:
            return 'matricula invalida.'

    if 'ano_compra' in data:
        ano = _parse_ano_compra(data.get('ano_compra'))
        if ano is None:
            return 'ano_compra deve ser um numero inteiro.'
        ano_atual = date.today().year
        if ano < 1980 or ano > ano_atual:
            return f'ano_compra deve estar entre 1980 e {ano_atual}.'

    if 'consumo_medio' in data:
        consumo = _parse_consumo_medio(data.get('consumo_medio'))
        if consumo is None:
            return 'consumo_medio deve ser um numero maior que 0.'

    if 'marca' in data and data['marca'] is not None:
        marca = str(data['marca']).strip()
        if len(marca) > 50:
            return 'marca demasiado longa.'

    if 'tipo_motor' in data and data['tipo_motor'] not in (None, ''):
        tm = str(data['tipo_motor']).strip().lower()
        if tm not in _MOTOR_VALIDOS:
            return "tipo_motor deve ser 'Gasolina', 'Diesel', 'Elétrico' ou 'Híbrido'."

    if 'nivel_conforto' in data and data['nivel_conforto'] not in (None, ''):
        nv = str(data['nivel_conforto']).strip().lower()
        if nv not in _NIVEL_VALIDOS:
            return "nivel_conforto deve ser 'Standard', 'Conforto' ou 'Premium'."

    return None


def _apply_taxi_updates(taxi: Taxi, data: dict) -> None:
    if 'modelo' in data:
        taxi.modelo = str(data['modelo']).strip()
    if 'matricula' in data:
        taxi.matricula = str(data['matricula']).strip().upper()
    if 'ano_compra' in data:
        taxi.ano_compra = int(data['ano_compra'])
    if 'consumo_medio' in data:
        consumo = _parse_consumo_medio(data.get('consumo_medio'))
        if consumo is not None:
            taxi.consumo_medio = consumo
    if 'marca' in data:
        taxi.marca = str(data['marca']).strip()[:50] if data['marca'] is not None else ''
    if 'tipo_motor' in data and data['tipo_motor'] not in (None, ''):
        tm = str(data['tipo_motor']).strip().lower()
        taxi.tipo_motor = _MOTOR_CANON.get(tm, taxi.tipo_motor)
    if 'nivel_conforto' in data and data['nivel_conforto'] not in (None, ''):
        nv = str(data['nivel_conforto']).strip().lower()
        taxi.nivel_conforto = _NIVEL_CANON.get(nv, taxi.nivel_conforto)


def _get_taxi_or_response(id_taxi):
    try:
        uid = id_taxi if isinstance(id_taxi, UUID) else UUID(str(id_taxi))
    except (ValueError, TypeError):
        return None, Response({'message': 'id_taxi invalido.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        return Taxi.objects.get(pk=uid), None
    except Taxi.DoesNotExist:
        return None, Response({'message': 'Taxi nao encontrado.'}, status=status.HTTP_404_NOT_FOUND)


def _apagar_taxi_instance(taxi: Taxi) -> Response:
    """Apaga um registo Taxi já carregado."""
    pk = str(taxi.id)
    taxi.delete()
    return Response(
        {'success': True, 'message': 'Taxi apagado.', 'id_taxi': pk},
        status=status.HTTP_200_OK,
    )


def _apagar_taxi_por_id(id_taxi) -> Response:
    """Resolve UUID, carrega o taxi e apaga (rota dedicada `apagar_taxi`)."""
    taxi, err_resp = _get_taxi_or_response(id_taxi)
    if err_resp:
        return err_resp
    assert taxi is not None
    return _apagar_taxi_instance(taxi)


def _consumo_para_calculo(data):
    """
    Resolve consumo_medio para o calculo:
    - se vier consumo_medio no payload, usa esse valor;
    - caso contrario, tenta obter por id_taxi.
    """
    consumo_payload = data.get('consumo_medio')
    if consumo_payload not in (None, ''):
        consumo = _parse_consumo_medio(consumo_payload)
        if consumo is None:
            return None, Response(
                {'message': 'consumo_medio deve ser um numero maior que 0.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return consumo, None

    id_taxi = data.get('id_taxi')
    if id_taxi in (None, ''):
        return None, Response(
            {'message': 'Envia consumo_medio ou id_taxi para calcular o valor da viagem.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    taxi, err_resp = _get_taxi_or_response(id_taxi)
    if err_resp:
        return None, err_resp
    assert taxi is not None
    return taxi.consumo_medio, None


# ---------------------------------------------------------------------------
# Views — CRUD
# ---------------------------------------------------------------------------


@api_view(['POST'])
def registo_taxi(request):
    body, err = _normalize_create_body(request.data)
    if err:
        return Response({'message': err}, status=status.HTTP_400_BAD_REQUEST)

    try:
        with transaction.atomic():
            taxi = Taxi.objects.create(**body)
    except IntegrityError:
        return Response({'message': 'Matricula ja registada.'}, status=status.HTTP_409_CONFLICT)

    return Response(
        {'success': True, 'taxi': _taxi_to_dict(taxi)},
        status=status.HTTP_201_CREATED,
    )


@api_view(['GET'])
def listar_taxis(request):
    taxis = list(Taxi.objects.all().order_by('matricula'))
    return Response(
        {
            'success': True,
            'taxis': [_taxi_to_dict(t) for t in taxis],
            'total': len(taxis),
        },
        status=status.HTTP_200_OK,
    )


@api_view(['GET', 'PATCH', 'PUT', 'DELETE'])
def gerir_taxi(request, id_taxi):
    taxi, err_resp = _get_taxi_or_response(id_taxi)
    if err_resp:
        return err_resp

    assert taxi is not None

    if request.method == 'GET':
        return Response({'success': True, 'taxi': _taxi_to_dict(taxi)}, status=status.HTTP_200_OK)

    if request.method == 'DELETE':
        return _apagar_taxi_instance(taxi)

    # PATCH / PUT
    data = request.data
    err = validate_taxi_update_payload(data)
    if err:
        return Response({'message': err}, status=status.HTTP_400_BAD_REQUEST)

    try:
        with transaction.atomic():
            _apply_taxi_updates(taxi, data)
            taxi.save()
    except IntegrityError:
        return Response({'message': 'Matricula ja registada.'}, status=status.HTTP_409_CONFLICT)

    taxi.refresh_from_db()
    return Response({'success': True, 'taxi': _taxi_to_dict(taxi)}, status=status.HTTP_200_OK)


@api_view(['DELETE'])
def apagar_taxi(request, id_taxi):
    """DELETE explícito: mesmo comportamento que DELETE em `gerir_taxi` (mesmo UUID)."""
    return _apagar_taxi_por_id(id_taxi)


@api_view(['POST'])
def calcular_valor_viagem(request):
    """
    Calcula o valor estimado da viagem com base em:
    - coordenadas de inicio/fim
    - consumo medio (payload ou id_taxi)

    Body esperado:
      {
        "inicio": {"lat": 40.64, "lng": -8.65},
        "fim": {"lat": 40.63, "lng": -8.64},
        "consumo_medio": 6.2,   # opcional se enviar id_taxi
        "id_taxi": "...",      # opcional se enviar consumo_medio
        "preco_combustivel": 1.80  # opcional (default 1.80 EUR/L)
      }
    """
    data = request.data or {}
    inicio = data.get('inicio') or {}
    fim = data.get('fim') or {}

    lat_ini, err = _parse_coordinate(inicio.get('lat'), 'inicio.lat')
    if err:
        return Response({'message': err}, status=status.HTTP_400_BAD_REQUEST)
    lng_ini, err = _parse_coordinate(inicio.get('lng'), 'inicio.lng')
    if err:
        return Response({'message': err}, status=status.HTTP_400_BAD_REQUEST)
    lat_fim, err = _parse_coordinate(fim.get('lat'), 'fim.lat')
    if err:
        return Response({'message': err}, status=status.HTTP_400_BAD_REQUEST)
    lng_fim, err = _parse_coordinate(fim.get('lng'), 'fim.lng')
    if err:
        return Response({'message': err}, status=status.HTTP_400_BAD_REQUEST)

    if not (-90 <= lat_ini <= 90 and -90 <= lat_fim <= 90):
        return Response({'message': 'Latitude deve estar entre -90 e 90.'}, status=status.HTTP_400_BAD_REQUEST)
    if not (-180 <= lng_ini <= 180 and -180 <= lng_fim <= 180):
        return Response({'message': 'Longitude deve estar entre -180 e 180.'}, status=status.HTTP_400_BAD_REQUEST)

    consumo_medio, consumo_err = _consumo_para_calculo(data)
    if consumo_err:
        return consumo_err

    preco_combustivel = _parse_consumo_medio(data.get('preco_combustivel', 1.80))
    if preco_combustivel is None:
        return Response({'message': 'preco_combustivel deve ser maior que 0.'}, status=status.HTTP_400_BAD_REQUEST)

    distancia_km = Decimal(str(_haversine_km(lat_ini, lng_ini, lat_fim, lng_fim)))
    litros_estimados = (distancia_km * Decimal(consumo_medio)) / Decimal('100')
    custo_estimado = litros_estimados * Decimal(preco_combustivel)

    return Response(
        {
            'success': True,
            'distancia_km': round(float(distancia_km), 3),
            'consumo_medio_l_100km': round(float(consumo_medio), 2),
            'litros_estimados': round(float(litros_estimados), 3),
            'preco_combustivel_eur_l': round(float(preco_combustivel), 3),
            'valor_estimado_eur': round(float(custo_estimado), 2),
        },
        status=status.HTTP_200_OK,
    )
