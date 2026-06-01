from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from math import atan2, cos, radians, sin, sqrt
from uuid import UUID

from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Taxi, PricingConfig
from apps.shift.models import Shift
from apps.trip.models import Trip

_NIVEL_CANON = {
    'básico': 'Básico',
    'luxuoso': 'Luxuoso',
}
_MOTOR_CANON = {
    'combustão': 'Combustão',
    'elétrico': 'Elétrico',
}
_NIVEL_VALIDOS = frozenset(_NIVEL_CANON.keys())
_MOTOR_VALIDOS = frozenset(_MOTOR_CANON.keys())
_TAXI_UPDATE_FIELDS = frozenset(('modelo', 'matricula', 'ano_compra', 'consumo_medio', 'marca', 'tipo_motor', 'nivel_conforto', 'estado', 'latitude', 'longitude'))
_ESTADO_VALIDOS = frozenset(('disponivel', 'indisponivel', 'ocupado'))
_TAXI_BRANDS = {
    'Toyota': {'Prius', 'Corolla', 'Camry', 'Yaris'},
    'Hyundai': {'Ioniq', 'i30', 'i20', 'Elantra'},
    'Kia': {'Niro', 'Ceed', 'Picanto', 'Sportage'},
    'Mercedes-Benz': {'E-Class', 'C-Class', 'A-Class', 'V-Class'},
    'BMW': {'3 Series', '5 Series', '1 Series', 'X5'},
    'Volkswagen': {'Passat', 'Golf', 'Polo', 'Tiguan'},
    'Renault': {'Megane', 'Clio', 'Espace', 'Scenic'},
    'Peugeot': {'308', '307', '3008', '5008'},
    'Citroën': {'C5', 'C3', 'C-Elysée', 'Berlingo'},
    'Fiat': {'500', 'Panda', 'Tipo', 'Ducato'},
    'Nissan': {'Qashqai', 'Altima', 'Micra', 'X-Trail'},
    'Chevrolet': {'Cruze', 'Spark', 'Cobalt', 'Onix'},
}

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
        'estado': taxi.estado,
        'latitude': float(taxi.latitude) if taxi.latitude is not None else None,
        'longitude': float(taxi.longitude) if taxi.longitude is not None else None,
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
        
    marca = str(data.get('marca', '')).strip()
    modelo = str(data.get('modelo', '')).strip()

    if marca not in _TAXI_BRANDS:
        return 'marca invalida. Deve ser selecionada da lista predefinida.'

    if modelo not in _TAXI_BRANDS[marca]:
        return 'modelo invalido para a marca selecionada.'

    if 'tipo_motor' in data and data.get('tipo_motor') not in (None, ''):
        tm = str(data['tipo_motor']).strip().lower()
        if tm not in _MOTOR_VALIDOS:
            return "tipo_motor deve ser 'Combustão' ou 'Elétrico'."

    if 'nivel_conforto' in data and data.get('nivel_conforto') not in (None, ''):
        nv = str(data['nivel_conforto']).strip().lower()
        if nv not in _NIVEL_VALIDOS:
            return "nivel_conforto deve ser 'Básico' ou 'Luxuoso'."

    return None


def _normalize_create_body(data):
    err = validate_taxi_payload(data)
    if err:
        return None, err

    marca = str(data.get('marca', '')).strip() if data.get('marca') is not None else ''
    motor = (str(data.get('tipo_motor', 'Combustão')).strip().lower()
             if data.get('tipo_motor') not in (None, '') else 'combustão')
    if motor not in _MOTOR_VALIDOS:
        motor = 'combustão'
    nivel = (str(data.get('nivel_conforto', 'Básico')).strip().lower()
             if data.get('nivel_conforto') not in (None, '') else 'básico')
    if nivel not in _NIVEL_VALIDOS:
        nivel = 'básico'

    return {
        'modelo': str(data['modelo']).strip(),
        'matricula': str(data['matricula']).strip().upper(),
        'ano_compra': int(data['ano_compra']),
        'consumo_medio': _parse_consumo_medio(data['consumo_medio']),
        'marca': marca[:50],
        'tipo_motor': _MOTOR_CANON.get(motor, 'Combustão'),
        'nivel_conforto': _NIVEL_CANON.get(nivel, 'Básico'),
        'estado': 'disponivel',  # Novos táxis começam sempre disponíveis
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
            return "tipo_motor deve ser 'Combustão' ou 'Elétrico'."

    if 'nivel_conforto' in data and data['nivel_conforto'] not in (None, ''):
        nv = str(data['nivel_conforto']).strip().lower()
        if nv not in _NIVEL_VALIDOS:
            return "nivel_conforto deve ser 'Básico' ou 'Luxuoso'."

    if 'estado' in data and data['estado'] not in (None, ''):
        estado = str(data['estado']).strip().lower()
        if estado not in _ESTADO_VALIDOS:
            return "estado deve ser 'disponivel', 'indisponivel' ou 'ocupado'."

    if 'latitude' in data and data['latitude'] is not None:
        lat, err = _parse_coordinate(data['latitude'], 'latitude')
        if err or not (-90 <= lat <= 90):
            return 'latitude deve estar entre -90 e 90.'

    if 'longitude' in data and data['longitude'] is not None:
        lng, err = _parse_coordinate(data['longitude'], 'longitude')
        if err or not (-180 <= lng <= 180):
            return 'longitude deve estar entre -180 e 180.'

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
    if 'estado' in data and data['estado'] not in (None, ''):
        estado = str(data['estado']).strip().lower()
        if estado in _ESTADO_VALIDOS:
            taxi.estado = estado
    if 'latitude' in data:
        if data['latitude'] is not None:
            lat, _ = _parse_coordinate(data['latitude'], 'latitude')
            taxi.latitude = lat
        else:
            taxi.latitude = None
    if 'longitude' in data:
        if data['longitude'] is not None:
            lng, _ = _parse_coordinate(data['longitude'], 'longitude')
            taxi.longitude = lng
        else:
            taxi.longitude = None


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
    """Apaga um registo Taxi já carregado, respeitando as regras do negócio."""
    tem_turnos = Shift.objects.filter(taxi_id=taxi.id).exists()

    if tem_turnos:
        return Response(
            {'message': 'Não é possível remover o táxi porque já foi requisitado para um turno.'},
            status=status.HTTP_409_CONFLICT,
        )

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
# Helpers — Gestão de Estado e Localização
# ---------------------------------------------------------------------------


def _marcar_taxi_disponivel(taxi: Taxi) -> None:
    """Marca o taxi como disponível."""
    taxi.estado = 'disponivel'
    taxi.save()


def _marcar_taxi_indisponivel(taxi: Taxi) -> None:
    """Marca o taxi como indisponível."""
    taxi.estado = 'indisponivel'
    taxi.save()


def _marcar_taxi_ocupado(taxi: Taxi) -> None:
    """Marca o taxi como ocupado."""
    taxi.estado = 'ocupado'
    taxi.save()


def _taxi_is_disponivel(taxi: Taxi) -> bool:
    """Verifica se o taxi está disponível."""
    return taxi.estado == 'disponivel'


def _taxi_is_indisponivel(taxi: Taxi) -> bool:
    """Verifica se o taxi está indisponível."""
    return taxi.estado == 'indisponivel'


def _taxi_is_ocupado(taxi: Taxi) -> bool:
    """Verifica se o taxi está ocupado."""
    return taxi.estado == 'ocupado'


def _atualizar_localizacao_taxi(taxi: Taxi, latitude: float, longitude: float) -> None:
    """Atualiza a localização (coordenadas GPS) do taxi."""
    taxi.latitude = latitude
    taxi.longitude = longitude
    taxi.save()


def _taxi_tem_localizacao(taxi: Taxi) -> bool:
    """Verifica se o taxi tem coordenadas registadas."""
    return taxi.latitude is not None and taxi.longitude is not None


def _taxi_get_localizacao(taxi: Taxi) -> tuple | None:
    """Retorna as coordenadas do taxi como tuplo (latitude, longitude)."""
    if _taxi_tem_localizacao(taxi):
        return (float(taxi.latitude), float(taxi.longitude))
    return None


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
    taxis = list(Taxi.objects.all().order_by('-updated_at'))
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
    
    marca_final = str(data.get('marca', taxi.marca)).strip()
    modelo_final = str(data.get('modelo', taxi.modelo)).strip()

    if marca_final not in _TAXI_BRANDS:
        return Response(
            {'message': 'marca invalida. Deve ser selecionada da lista predefinida.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if modelo_final not in _TAXI_BRANDS[marca_final]:
        return Response(
            {'message': 'modelo invalido para a marca selecionada.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    if 'nivel_conforto' in data:
        tem_viagens = Trip.objects.filter(taxi_id=taxi.id).exists()

        if tem_viagens:
            return Response(
                {
                    'message': 'Não é possível alterar o nível de conforto porque o táxi já fez viagens com clientes.'
                },
                status=status.HTTP_409_CONFLICT,
            )
        
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


# ---------------------------------------------------------------------------
# Views — Gestão de Estado e Localização
# ---------------------------------------------------------------------------


@api_view(['PATCH', 'PUT', 'POST'])
def atualizar_estado_taxi(request, id_taxi):
    """
    Atualiza o estado do taxi.

    Body esperado:
      {
        "estado": "disponivel"  # ou "indisponivel" / "ocupado"
      }

    Também suporta os métodos de conveniência:
      - POST /taxi/{id}/estado com "action": "disponivel" etc.
    """
    taxi, err_resp = _get_taxi_or_response(id_taxi)
    if err_resp:
        return err_resp

    assert taxi is not None

    data = request.data or {}
    estado = data.get('estado') or data.get('action')

    if not estado:
        return Response(
            {'message': 'Campo "estado" ou "action" é obrigatório.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    estado = str(estado).strip().lower()
    if estado not in _ESTADO_VALIDOS:
        return Response(
            {'message': f"Estado deve ser um de: {', '.join(_ESTADO_VALIDOS)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    taxi.estado = estado
    taxi.save()
    taxi.refresh_from_db()

    return Response(
        {
            'success': True,
            'message': f'Estado do taxi atualizado para: {estado}',
            'taxi': _taxi_to_dict(taxi),
        },
        status=status.HTTP_200_OK,
    )


@api_view(['PATCH', 'PUT', 'POST'])
def atualizar_localizacao_taxi(request, id_taxi):
    """
    Atualiza a localização (coordenadas GPS) do taxi.

    Body esperado:
      {
        "latitude": 40.6366,
        "longitude": -8.6538
      }
    """
    taxi, err_resp = _get_taxi_or_response(id_taxi)
    if err_resp:
        return err_resp

    assert taxi is not None

    data = request.data or {}
    latitude = data.get('latitude')
    longitude = data.get('longitude')

    if latitude is None or longitude is None:
        return Response(
            {'message': 'Campos "latitude" e "longitude" são obrigatórios.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    lat, lat_err = _parse_coordinate(latitude, 'latitude')
    if lat_err:
        return Response({'message': lat_err}, status=status.HTTP_400_BAD_REQUEST)

    lng, lng_err = _parse_coordinate(longitude, 'longitude')
    if lng_err:
        return Response({'message': lng_err}, status=status.HTTP_400_BAD_REQUEST)

    if not (-90 <= lat <= 90):
        return Response(
            {'message': 'Latitude deve estar entre -90 e 90.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not (-180 <= lng <= 180):
        return Response(
            {'message': 'Longitude deve estar entre -180 e 180.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    _atualizar_localizacao_taxi(taxi, lat, lng)
    taxi.refresh_from_db()

    return Response(
        {
            'success': True,
            'message': 'Localização do taxi atualizada.',
            'taxi': _taxi_to_dict(taxi),
        },
        status=status.HTTP_200_OK,
    )


# ---------------------------------------------------------------------------
# Views — Pricing (algoritmo com multiplier de conforto)
# ---------------------------------------------------------------------------

@api_view(['POST'])
def calcular_preco_com_conforto(request):
    """
    Calcula o preço da viagem usando o algoritmo dinâmico com multiplicador de conforto.
    
    Este endpoint é simples e rápido para usar no frontend.
    
    Body esperado:
      {
        "distancia_km": 12.2,
        "duracao_minutos": 20,
        "nivel_conforto": "Standard"  # ou "Conforto", "Premium"
      }
    
    Response:
      {
        "success": true,
        "price": 7.96,
        "comfort_level": "Standard",
        "breakdown": { ... }
      }
    """
    from .pricing_service import PricingService
    
    data = request.data or {}
    
    try:
        distancia_km = float(data.get('distancia_km', 0))
        duracao_minutos = int(data.get('duracao_minutos', 0))
        nivel_conforto = str(data.get('nivel_conforto', 'Standard')).strip()
    except (TypeError, ValueError):
        return Response(
            {'message': 'distancia_km (float), duracao_minutos (int) e nivel_conforto (string) são obrigatórios.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    try:
        result = PricingService.calculate_price_by_distance(
            distance_km=distancia_km,
            duration_minutes=duracao_minutos,
            comfort_level=nivel_conforto
        )
        return Response(
            {'success': True, **result},
            status=status.HTTP_200_OK,
        )
    except ValueError as e:
        return Response(
            {'message': str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )

# ---------------------------------------------------------------------------
# Views — Pricing configurável da User Story 3
# ---------------------------------------------------------------------------

def _pricing_config_to_dict(config: PricingConfig) -> dict:
    return {
        "id": str(config.id),
        "preco_basico_minuto": float(config.preco_basico_minuto),
        "preco_luxuoso_minuto": float(config.preco_luxuoso_minuto),
        "agravamento_noturno_percentual": float(config.agravamento_noturno_percentual),
        "updated_at": config.updated_at.isoformat() if config.updated_at else None,
    }


def _parse_decimal_positivo(raw, field_name, permite_zero=False):
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, TypeError, ValueError):
        return None, f"{field_name} deve ser um número válido."

    if permite_zero:
        if value < 0:
            return None, f"{field_name} não pode ser negativo."
    else:
        if value <= 0:
            return None, f"{field_name} deve ser maior que 0."

    return value, None


@api_view(["GET", "PATCH", "PUT"])
def pricing_config(request):
    """
    GET/PATCH da configuração de preços.

    Campos:
    - preco_basico_minuto
    - preco_luxuoso_minuto
    - agravamento_noturno_percentual
    """

    config = PricingConfig.get_config()

    if request.method == "GET":
        return Response(
            {
                "success": True,
                "pricing": _pricing_config_to_dict(config),
            },
            status=status.HTTP_200_OK,
        )

    data = request.data or {}

    if "preco_basico_minuto" in data:
        value, err = _parse_decimal_positivo(
            data.get("preco_basico_minuto"),
            "preco_basico_minuto",
        )
        if err:
            return Response({"message": err}, status=status.HTTP_400_BAD_REQUEST)

        config.preco_basico_minuto = value

    if "preco_luxuoso_minuto" in data:
        value, err = _parse_decimal_positivo(
            data.get("preco_luxuoso_minuto"),
            "preco_luxuoso_minuto",
        )
        if err:
            return Response({"message": err}, status=status.HTTP_400_BAD_REQUEST)

        config.preco_luxuoso_minuto = value

    if "agravamento_noturno_percentual" in data:
        value, err = _parse_decimal_positivo(
            data.get("agravamento_noturno_percentual"),
            "agravamento_noturno_percentual",
            permite_zero=True,
        )
        if err:
            return Response({"message": err}, status=status.HTTP_400_BAD_REQUEST)

        config.agravamento_noturno_percentual = value

    config.save()

    return Response(
        {
            "success": True,
            "message": "Configuração de preços atualizada.",
            "pricing": _pricing_config_to_dict(config),
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
def simular_preco_viagem(request):
    """
    Simula o preço de uma viagem fictícia entre duas datas/horas.

    Body esperado:
      {
        "start_datetime": "2026-06-01T20:00",
        "end_datetime": "2026-06-01T21:30",
        "nivel_conforto": "Luxuoso"
      }
    """

    from django.utils import timezone
    from django.utils.dateparse import parse_datetime
    from .pricing_service import PricingService

    data = request.data or {}

    start_raw = data.get("start_datetime")
    end_raw = data.get("end_datetime")
    nivel_conforto = str(data.get("nivel_conforto", "")).strip()

    if not start_raw or not end_raw:
        return Response(
            {"message": "start_datetime e end_datetime são obrigatórios."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if nivel_conforto not in ("Básico", "Luxuoso"):
        return Response(
            {"message": "nivel_conforto deve ser 'Básico' ou 'Luxuoso'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    start_dt = parse_datetime(str(start_raw))
    end_dt = parse_datetime(str(end_raw))

    if not start_dt or not end_dt:
        return Response(
            {"message": "Datas inválidas."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if timezone.is_naive(start_dt):
        start_dt = timezone.make_aware(start_dt)

    if timezone.is_naive(end_dt):
        end_dt = timezone.make_aware(end_dt)

    try:
        result = PricingService.calculate_price(
            start_datetime=start_dt,
            end_datetime=end_dt,
            comfort_level=nivel_conforto,
        )

        return Response(
            {
                "success": True,
                **result,
            },
            status=status.HTTP_200_OK,
        )
    except ValueError as e:
        return Response(
            {"message": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )