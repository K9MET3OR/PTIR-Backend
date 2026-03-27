from __future__ import annotations

from datetime import date
from uuid import UUID

from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Taxi

_NIVEL_VALIDOS = frozenset(('baixo', 'medio', 'alto'))
_TAXI_UPDATE_FIELDS = frozenset(('modelo', 'matricula', 'ano_compra', 'marca', 'nivel_conforto'))

# ---------------------------------------------------------------------------
# Helpers — serialização
# ---------------------------------------------------------------------------


def _taxi_to_dict(taxi: Taxi) -> dict:
    return {
        'id_taxi': str(taxi.id_taxi),
        'modelo': taxi.modelo,
        'matricula': taxi.matricula,
        'ano_compra': taxi.ano_compra,
        'marca': taxi.marca or '',
        'nivel_conforto': taxi.nivel_conforto,
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


def validate_taxi_payload(data):
    """
    Valida o corpo para POST / registo.
    Devolve mensagem de erro ou None se estiver correto.
    """
    required = ('modelo', 'matricula', 'ano_compra')
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

    if 'marca' in data and data.get('marca') not in (None, ''):
        marca = str(data['marca']).strip()
        if len(marca) > 50:
            return 'marca demasiado longa.'

    if 'nivel_conforto' in data and data.get('nivel_conforto') not in (None, ''):
        nv = str(data['nivel_conforto']).strip().lower()
        if nv not in _NIVEL_VALIDOS:
            return "nivel_conforto deve ser 'baixo', 'medio' ou 'alto'."

    return None


def _normalize_create_body(data):
    err = validate_taxi_payload(data)
    if err:
        return None, err

    marca = str(data.get('marca', '')).strip() if data.get('marca') is not None else ''
    nivel = (str(data.get('nivel_conforto', 'medio')).strip().lower()
             if data.get('nivel_conforto') not in (None, '') else 'medio')
    if nivel not in _NIVEL_VALIDOS:
        nivel = 'medio'

    return {
        'modelo': str(data['modelo']).strip(),
        'matricula': str(data['matricula']).strip().upper(),
        'ano_compra': int(data['ano_compra']),
        'marca': marca[:50],
        'nivel_conforto': nivel,
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

    if 'marca' in data and data['marca'] is not None:
        marca = str(data['marca']).strip()
        if len(marca) > 50:
            return 'marca demasiado longa.'

    if 'nivel_conforto' in data and data['nivel_conforto'] not in (None, ''):
        nv = str(data['nivel_conforto']).strip().lower()
        if nv not in _NIVEL_VALIDOS:
            return "nivel_conforto deve ser 'baixo', 'medio' ou 'alto'."

    return None


def _apply_taxi_updates(taxi: Taxi, data: dict) -> None:
    if 'modelo' in data:
        taxi.modelo = str(data['modelo']).strip()
    if 'matricula' in data:
        taxi.matricula = str(data['matricula']).strip().upper()
    if 'ano_compra' in data:
        taxi.ano_compra = int(data['ano_compra'])
    if 'marca' in data:
        taxi.marca = str(data['marca']).strip()[:50] if data['marca'] is not None else ''
    if 'nivel_conforto' in data and data['nivel_conforto'] not in (None, ''):
        taxi.nivel_conforto = str(data['nivel_conforto']).strip().lower()


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
    pk = str(taxi.id_taxi)
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
