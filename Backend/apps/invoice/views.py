import re
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Invoice
from apps.trip.models import Trip


def validar_nif(nif):
    return bool(re.match(r"^\d{9}$", str(nif or "").strip()))


def obter_nif_cliente(trip):
    """
    Obtém o NIF do cliente associado à viagem.
    Como Client herda de User, em princípio trip.client.nif deve existir.
    """
    try:
        return getattr(trip.client, "nif", None)
    except Exception:
        return None


def invoice_para_json(invoice):
    trip = invoice.trip
    client_nif = obter_nif_cliente(trip)

    return {
        "id": str(invoice.id),
        "trip_id": str(invoice.trip_id),

        "n_fatura": invoice.n_fatura,
        "ano": invoice.ano,
        "numero_formatado": f"{invoice.n_fatura}/{invoice.ano}",

        "data": invoice.data.isoformat() if invoice.data else None,

        # A API devolve "valor", mesmo que o campo no modelo se chame price.
        "valor": str(invoice.price),

        "client_id": str(trip.client_id) if trip.client_id else None,
        "client_nif": client_nif or "",

        "driver_id": str(trip.driver_id) if trip.driver_id else None,
        "taxi_id": str(trip.taxi_id) if trip.taxi_id else None,

        "start_location": trip.start_location,
        "end_location": trip.end_location,
        "start_date": trip.start_date.isoformat() if trip.start_date else None,
        "end_date": trip.end_date.isoformat() if trip.end_date else None,
        "n_kms": str(trip.n_kms) if trip.n_kms is not None else None,
    }


def gerar_numero_fatura(ano):
    ultima = Invoice.objects.filter(ano=ano).order_by("-n_fatura").first()
    return 1 if not ultima else ultima.n_fatura + 1


@api_view(["POST"])
def register_invoice(request):
    trip_id = request.data.get("trip_id")

    if not trip_id:
        return Response({"message": "trip_id é obrigatório."}, status=400)

    trip = Trip.objects.filter(pk=trip_id).first()

    if not trip:
        return Response({"message": "Viagem não encontrada."}, status=404)

    if trip.status_trip != "finished":
        return Response(
            {"message": "Só é possível emitir fatura para viagens pagas e finalizadas."},
            status=400,
        )

    if Invoice.objects.filter(trip=trip).exists():
        return Response(
            {"message": "Já existe uma fatura para esta viagem."},
            status=409,
        )

    if not trip.start_date:
        return Response(
            {"message": "A viagem não tem data de início."},
            status=400,
        )

    if not trip.end_date:
        return Response(
            {"message": "A viagem não tem data de fim."},
            status=400,
        )

    if trip.end_date <= trip.start_date:
        return Response(
            {"message": "A data de fim da viagem tem de ser posterior à data de início."},
            status=400,
        )

    data_fatura = timezone.now()

    if data_fatura < trip.end_date:
        return Response(
            {"message": "A data da fatura tem de ser posterior ou igual ao fim da viagem."},
            status=400,
        )

    if trip.price is None or trip.price <= 0:
        return Response(
            {"message": "O preço da viagem tem de ser positivo."},
            status=400,
        )

    if not trip.client_id:
        return Response(
            {"message": "A viagem não tem cliente associado."},
            status=400,
        )

    if not trip.driver_id:
        return Response(
            {"message": "A viagem não tem motorista associado."},
            status=400,
        )

    client_nif = obter_nif_cliente(trip)

    if not validar_nif(client_nif):
        return Response(
            {"message": "O NIF do cliente é inválido ou não está associado."},
            status=400,
        )

    try:
        with transaction.atomic():
            ano = data_fatura.year
            n_fatura = gerar_numero_fatura(ano)

            invoice = Invoice.objects.create(
                trip=trip,
                n_fatura=n_fatura,
                ano=ano,
                data=data_fatura,
                price=trip.price,
            )

    except IntegrityError:
        return Response(
            {
                "message": (
                    "Erro ao emitir fatura. Pode já existir uma fatura para esta viagem "
                    "ou uma fatura com esse número."
                )
            },
            status=409,
        )

    return Response(
        {
            "success": True,
            "invoice": invoice_para_json(invoice),
        },
        status=201,
    )


@api_view(["GET"])
def listar_invoices(request):
    invoices = Invoice.objects.all().order_by("-data")

    return Response(
        {
            "success": True,
            "invoices": [invoice_para_json(invoice) for invoice in invoices],
            "total": invoices.count(),
        },
        status=200,
    )


@api_view(["GET"])
def listar_invoices_driver(request, driver_id):
    invoices = Invoice.objects.filter(
        trip__driver_id=driver_id
    ).order_by("-data")

    return Response(
        {
            "success": True,
            "driver_id": str(driver_id),
            "invoices": [invoice_para_json(invoice) for invoice in invoices],
            "total": invoices.count(),
        },
        status=200,
    )


@api_view(["GET"])
def gerir_invoice(request, id_invoice):
    invoice = Invoice.objects.filter(pk=id_invoice).first()

    if not invoice:
        return Response({"message": "Fatura não encontrada."}, status=404)

    return Response(
        {
            "success": True,
            "invoice": invoice_para_json(invoice),
        },
        status=200,
    )