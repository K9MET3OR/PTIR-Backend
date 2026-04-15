from django.db import IntegrityError
from django.utils.dateparse import parse_datetime
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Shift
from apps.taxi.models import Taxi
from apps.user.driver.models import Driver


def shift_para_json(shift):
    return {
        "id": str(shift.id),
        "driver_id": str(shift.driver_id),
        "taxi_id": str(shift.taxi_id),
        "start_date": shift.start_date,
        "end_date": shift.end_date,
        "status_shift": shift.status_shift,
        "created_at": shift.created_at,
        "updated_at": shift.updated_at,
    }


def taxi_para_json(taxi):
    return {
        "id": str(taxi.id),
        "modelo": taxi.modelo,
        "matricula": taxi.matricula,
        "ano_compra": taxi.ano_compra,
        "marca": taxi.marca,
        "nivel_conforto": taxi.nivel_conforto,
        "tipo_motor": taxi.tipo_motor,
        "consumo_medio": taxi.consumo_medio,
    }


def turno_interseta_outro(driver_id, start_date, end_date, excluir_shift_id=None):
    qs = Shift.objects.filter(
        driver_id=driver_id,
        start_date__lt=end_date,
        end_date__gt=start_date
    )

    if excluir_shift_id:
        qs = qs.exclude(pk=excluir_shift_id)

    return qs.exists()


def obter_taxis_ocupados(start_date, end_date):
    return Shift.objects.filter(
        start_date__lt=end_date,
        end_date__gt=start_date
    ).values_list("taxi_id", flat=True)


@api_view(["GET"])
def listar_shifts(request):
    shifts = Shift.objects.all().order_by("start_date")

    resultado = []
    for shift in shifts:
        resultado.append(shift_para_json(shift))

    return Response(
        {
            "success": True,
            "shifts": resultado,
            "total": len(resultado),
        },
        status=200,
    )


@api_view(["GET"])
def listar_shifts_driver(request, driver_id):
    driver = Driver.objects.filter(pk=driver_id).first()

    if not driver:
        return Response({"message": "Driver não encontrado."}, status=404)

    shifts = Shift.objects.filter(driver_id=driver_id).order_by("start_date")

    resultado = []
    for shift in shifts:
        resultado.append(shift_para_json(shift))

    return Response(
        {
            "success": True,
            "driver_id": str(driver_id),
            "shifts": resultado,
            "total": len(resultado),
        },
        status=200,
    )


@api_view(["GET"])
def taxis_disponiveis(request):
    start_date_str = request.GET.get("start_date")
    end_date_str = request.GET.get("end_date")

    if not start_date_str or not end_date_str:
        return Response(
            {"message": "start_date e end_date são obrigatórios."},
            status=400,
        )

    start_date = parse_datetime(start_date_str)
    end_date = parse_datetime(end_date_str)

    if not start_date or not end_date:
        return Response(
            {"message": "Datas inválidas. Usa formato ISO 8601."},
            status=400,
        )

    if start_date >= end_date:
        return Response(
            {"message": "O início do turno deve ser anterior ao fim."},
            status=400,
        )

    taxis_ocupados = obter_taxis_ocupados(start_date, end_date)
    taxis = Taxi.objects.exclude(id__in=taxis_ocupados).order_by("id")

    resultado = []
    for taxi in taxis:
        resultado.append(taxi_para_json(taxi))

    return Response(
        {
            "success": True,
            "taxis": resultado,
            "total": len(resultado),
        },
        status=200,
    )


@api_view(["POST"])
def registar_shift(request):
    data = request.data

    driver_id = data.get("driver")
    taxi_id = data.get("taxi")
    start_date_str = data.get("start_date")
    end_date_str = data.get("end_date")

    if not driver_id:
        return Response({"message": "driver é obrigatório."}, status=400)

    if not taxi_id:
        return Response({"message": "taxi é obrigatório."}, status=400)

    if not start_date_str:
        return Response({"message": "start_date é obrigatório."}, status=400)

    if not end_date_str:
        return Response({"message": "end_date é obrigatório."}, status=400)

    driver = Driver.objects.filter(pk=driver_id).first()
    if not driver:
        return Response({"message": "Driver não encontrado."}, status=404)

    taxi = Taxi.objects.filter(pk=taxi_id).first()
    if not taxi:
        return Response({"message": "Taxi não encontrado."}, status=404)

    start_date = parse_datetime(str(start_date_str))
    end_date = parse_datetime(str(end_date_str))

    if not start_date or not end_date:
        return Response(
            {"message": "Datas inválidas. Usa formato ISO 8601."},
            status=400,
        )

    if start_date >= end_date:
        return Response(
            {"message": "O início do turno deve ser anterior ao fim."},
            status=400,
        )

    duracao = end_date - start_date
    duracao_horas = duracao.total_seconds() / 3600

    if duracao_horas <= 0:
        return Response(
            {"message": "A duração do turno tem de ser positiva."},
            status=400,
        )

    if duracao_horas > 8:
        return Response(
            {"message": "A duração do turno não pode exceder 8 horas."},
            status=400,
        )

    if turno_interseta_outro(driver.id, start_date, end_date):
        return Response(
            {"message": "O turno interseta outro turno do mesmo motorista."},
            status=400,
        )

    taxi_ocupado = Shift.objects.filter(
        taxi_id=taxi.id,
        start_date__lt=end_date,
        end_date__gt=start_date
    ).exists()

    if taxi_ocupado:
        return Response(
            {"message": "O táxi não está disponível para esse turno."},
            status=400,
        )

    try:
        shift = Shift.objects.create(
            driver_id=driver.id,
            taxi_id=taxi.id,
            start_date=start_date,
            end_date=end_date,
            status_shift=data.get("status_shift", "active"),
        )
    except IntegrityError:
        return Response({"message": "Erro ao registar shift."}, status=409)

    return Response(
        {
            "success": True,
            "shift": shift_para_json(shift),
        },
        status=201,
    )


@api_view(["GET", "PATCH", "PUT", "DELETE"])
def gerir_shift(request, id_shift):
    shift = Shift.objects.filter(pk=id_shift).first()

    if not shift:
        return Response({"message": "Shift não encontrado."}, status=404)

    if request.method == "GET":
        return Response(
            {
                "success": True,
                "shift": shift_para_json(shift),
            },
            status=200,
        )

    if request.method == "DELETE":
        shift_id = str(shift.id)
        shift.delete()

        return Response(
            {
                "success": True,
                "message": "Shift apagado.",
                "id": shift_id,
            },
            status=200,
        )

    data = request.data

    driver_id = data.get("driver", shift.driver_id)
    taxi_id = data.get("taxi", shift.taxi_id)
    start_date_str = data.get("start_date", shift.start_date.isoformat())
    end_date_str = data.get("end_date", shift.end_date.isoformat())

    driver = Driver.objects.filter(pk=driver_id).first()
    if not driver:
        return Response({"message": "Driver não encontrado."}, status=404)

    taxi = Taxi.objects.filter(pk=taxi_id).first()
    if not taxi:
        return Response({"message": "Taxi não encontrado."}, status=404)

    start_date = parse_datetime(str(start_date_str)) if isinstance(start_date_str, str) else start_date_str
    end_date = parse_datetime(str(end_date_str)) if isinstance(end_date_str, str) else end_date_str

    if not start_date or not end_date:
        return Response(
            {"message": "Datas inválidas. Usa formato ISO 8601."},
            status=400,
        )

    if start_date >= end_date:
        return Response(
            {"message": "O início do turno deve ser anterior ao fim."},
            status=400,
        )

    duracao = end_date - start_date
    duracao_horas = duracao.total_seconds() / 3600

    if duracao_horas <= 0:
        return Response(
            {"message": "A duração do turno tem de ser positiva."},
            status=400,
        )

    if duracao_horas > 8:
        return Response(
            {"message": "A duração do turno não pode exceder 8 horas."},
            status=400,
        )

    if turno_interseta_outro(driver.id, start_date, end_date, excluir_shift_id=shift.id):
        return Response(
            {"message": "O turno interseta outro turno do mesmo motorista."},
            status=400,
        )

    taxi_ocupado = Shift.objects.filter(
        taxi_id=taxi.id,
        start_date__lt=end_date,
        end_date__gt=start_date
    ).exclude(pk=shift.id).exists()

    if taxi_ocupado:
        return Response(
            {"message": "O táxi não está disponível para esse turno."},
            status=400,
        )

    shift.driver_id = driver.id
    shift.taxi_id = taxi.id
    shift.start_date = start_date
    shift.end_date = end_date

    if "status_shift" in data:
        shift.status_shift = data["status_shift"]

    try:
        shift.save()
    except IntegrityError:
        return Response({"message": "Erro ao atualizar shift."}, status=409)

    return Response(
        {
            "success": True,
            "shift": shift_para_json(shift),
        },
        status=200,
    )