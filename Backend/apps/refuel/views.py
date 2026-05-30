from decimal import Decimal, InvalidOperation

from django.db import IntegrityError
from django.utils.dateparse import parse_datetime
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Refuel
from apps.shift.models import Shift
from apps.user.views import firebase_auth_required, get_user_from_request


def refuel_para_json(refuel):
    return {
        "id": str(refuel.id),
        "shift_id": str(refuel.shift_id),
        "taxi_id": str(refuel.taxi_id),
        "data_inicio": refuel.data_inicio.isoformat() if refuel.data_inicio else None,
        "data_fim": refuel.data_fim.isoformat() if refuel.data_fim else None,
        "tipo": refuel.tipo,
        "litros": str(refuel.litros) if refuel.litros is not None else None,
        "kwh": str(refuel.kwh) if refuel.kwh is not None else None,
        "euros_pagos": str(refuel.euros_pagos),
        "kms_taxi": str(refuel.kms_taxi),
        "created_at": refuel.created_at.isoformat() if refuel.created_at else None,
    }


def to_decimal(value, field_name):
    try:
        value = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None, f"{field_name} inválido."

    return value, None


def motor_eletrico(tipo_motor):
    return str(tipo_motor).strip().lower() in ["eletrico", "elétrico", "electric"]


@api_view(["POST"])
@firebase_auth_required
def registar_refuel(request):
    data = request.data

    shift_id = data.get("shift")

    if not shift_id:
        return Response({"message": "shift é obrigatório."}, status=400)

    shift = Shift.objects.filter(pk=shift_id).first()

    if not shift:
        return Response({"message": "Turno não encontrado."}, status=404)

    taxi = shift.taxi
    tipo_motor = taxi.tipo_motor

    data_inicio = parse_datetime(str(data.get("data_inicio", "")))
    data_fim = parse_datetime(str(data.get("data_fim", "")))

    if not data_inicio or not data_fim:
        return Response(
            {"message": "data_inicio e data_fim são obrigatórias e devem estar em formato válido."},
            status=400,
        )

    if data_inicio >= data_fim:
        return Response(
            {"message": "A data de início deve ser anterior à data de fim."},
            status=400,
        )

    is_eletrico = motor_eletrico(tipo_motor)

    if is_eletrico:
        if not (shift.start_date <= data_inicio <= shift.end_date):
            return Response(
                {"message": "Em táxis elétricos, o início do carregamento deve ocorrer dentro do turno."},
                status=400,
            )
    else:
        if not (shift.start_date <= data_inicio and data_fim <= shift.end_date):
            return Response(
                {"message": "Em táxis a combustão, o reabastecimento deve ocorrer dentro do turno."},
                status=400,
            )

    euros_pagos, err = to_decimal(data.get("euros_pagos"), "euros_pagos")
    if err:
        return Response({"message": err}, status=400)

    kms_taxi, err = to_decimal(data.get("kms_taxi"), "kms_taxi")
    if err:
        return Response({"message": err}, status=400)

    if euros_pagos <= 0:
        return Response({"message": "euros_pagos deve ser superior a 0."}, status=400)

    if kms_taxi < 0:
        return Response({"message": "kms_taxi não pode ser negativo."}, status=400)

    litros = None
    kwh = None

    if is_eletrico:
        kwh, err = to_decimal(data.get("kwh"), "kwh")
        if err:
            return Response({"message": err}, status=400)

        if kwh <= 0:
            return Response({"message": "kwh deve ser superior a 0."}, status=400)

    else:
        litros, err = to_decimal(data.get("litros"), "litros")
        if err:
            return Response({"message": err}, status=400)

        if litros <= 0:
            return Response({"message": "litros deve ser superior a 0."}, status=400)

    try:
        refuel = Refuel.objects.create(
            shift=shift,
            taxi=taxi,
            data_inicio=data_inicio,
            data_fim=data_fim,
            tipo=tipo_motor,
            litros=litros,
            kwh=kwh,
            euros_pagos=euros_pagos,
            kms_taxi=kms_taxi,
        )
    except IntegrityError:
        return Response({"message": "Erro ao registar reabastecimento."}, status=409)

    return Response(
        {
            "success": True,
            "refuel": refuel_para_json(refuel),
        },
        status=201,
    )


@api_view(["GET"])
@firebase_auth_required
def listar_refuels(request):
    refuels = Refuel.objects.all().order_by("-data_inicio")

    return Response(
        {
            "success": True,
            "refuels": [refuel_para_json(refuel) for refuel in refuels],
            "total": refuels.count(),
        },
        status=200,
    )


@api_view(["GET"])
@firebase_auth_required
def listar_refuels_taxi(request, taxi_id):
    refuels = Refuel.objects.filter(taxi_id=taxi_id).order_by("-data_inicio")

    return Response(
        {
            "success": True,
            "taxi_id": str(taxi_id),
            "refuels": [refuel_para_json(refuel) for refuel in refuels],
            "total": refuels.count(),
        },
        status=200,
    )


@api_view(["GET", "DELETE"])
@firebase_auth_required
def gerir_refuel(request, id_refuel):
    refuel = Refuel.objects.filter(pk=id_refuel).first()

    if not refuel:
        return Response({"message": "Reabastecimento não encontrado."}, status=404)

    if request.method == "GET":
        return Response(
            {
                "success": True,
                "refuel": refuel_para_json(refuel),
            },
            status=200,
        )

    if request.method == "DELETE":
        refuel_id = str(refuel.id)
        refuel.delete()

        return Response(
            {
                "success": True,
                "message": "Reabastecimento apagado.",
                "id": refuel_id,
            },
            status=200,
        )