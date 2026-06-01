from datetime import timedelta
from decimal import Decimal
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Count, F, ExpressionWrapper, DurationField
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.trip.models import Trip
from apps.invoice.models import Invoice
from apps.refuel.models import Refuel
from apps.taxi.models import Taxi
from apps.user.driver.models import Driver


def get_period(request):
    today = timezone.localdate()

    start = parse_date(request.GET.get("start", "")) or today
    end = parse_date(request.GET.get("end", "")) or today

    start_dt = timezone.make_aware(timezone.datetime.combine(start, timezone.datetime.min.time()))
    end_dt = timezone.make_aware(timezone.datetime.combine(end, timezone.datetime.max.time()))

    return start_dt, end_dt


def duration_hours(duration):
    if not duration:
        return 0
    return round(duration.total_seconds() / 3600, 2)


@api_view(["GET"])
def trips_summary(request):
    start_dt, end_dt = get_period(request)

    duration_expr = ExpressionWrapper(
        F("end_date") - F("start_date"),
        output_field=DurationField()
    )

    trips = Trip.objects.filter(
        start_date__gte=start_dt,
        start_date__lte=end_dt,
        status_trip="finished",
    )

    total = trips.annotate(duration=duration_expr).aggregate(
        total_trips=Count("id"),
        total_kms=Sum("n_kms"),
        total_duration=Sum("duration"),
    )

    return Response({
        "success": True,
        "period": {"start": start_dt, "end": end_dt},
        "total_trips": total["total_trips"] or 0,
        "total_kms": str(total["total_kms"] or Decimal("0")),
        "total_hours": duration_hours(total["total_duration"]),
    })


@api_view(["GET"])
def trips_by_driver(request):
    start_dt, end_dt = get_period(request)

    duration_expr = ExpressionWrapper(
        F("end_date") - F("start_date"),
        output_field=DurationField()
    )

    rows = Trip.objects.filter(
        start_date__gte=start_dt,
        start_date__lte=end_dt,
        status_trip="finished",
        driver_id__isnull=False,
    ).annotate(duration=duration_expr).values(
        "driver_id"
    ).annotate(
        total_trips=Count("id"),
        total_kms=Sum("n_kms"),
        total_duration=Sum("duration"),
    ).order_by("-total_trips")

    return Response({
        "success": True,
        "drivers": [
            {
                "driver_id": str(row["driver_id"]),
                "total_trips": row["total_trips"],
                "total_kms": str(row["total_kms"] or Decimal("0")),
                "total_hours": duration_hours(row["total_duration"]),
            }
            for row in rows
        ]
    })


@api_view(["GET"])
def trips_by_taxi(request):
    start_dt, end_dt = get_period(request)

    duration_expr = ExpressionWrapper(
        F("end_date") - F("start_date"),
        output_field=DurationField()
    )

    rows = Trip.objects.filter(
        start_date__gte=start_dt,
        start_date__lte=end_dt,
        status_trip="finished",
        taxi_id__isnull=False,
    ).annotate(duration=duration_expr).values(
        "taxi_id"
    ).annotate(
        total_trips=Count("id"),
        total_kms=Sum("n_kms"),
        total_duration=Sum("duration"),
    ).order_by("-total_trips")

    return Response({
        "success": True,
        "taxis": [
            {
                "taxi_id": str(row["taxi_id"]),
                "total_trips": row["total_trips"],
                "total_kms": str(row["total_kms"] or Decimal("0")),
                "total_hours": duration_hours(row["total_duration"]),
            }
            for row in rows
        ]
    })

def serialize_trip(trip):
    duration = None

    if trip.start_date and trip.end_date:
        duration = trip.end_date - trip.start_date

    return {
        "id": trip.id,
        "start_date": trip.start_date,
        "end_date": trip.end_date,
        "duration_hours": duration_hours(duration),
        "n_kms": str(trip.n_kms or Decimal("0")),
        "price": str(getattr(trip, "price", Decimal("0")) or Decimal("0")),
        "status_trip": trip.status_trip,
        "driver_id": trip.driver_id,
        "taxi_id": str(trip.taxi_id) if trip.taxi_id else None,
        "client_id": trip.client_id,
        "start_location": getattr(trip, "start_location", None),
        "end_location": getattr(trip, "end_location", None),
    }


def serialize_taxi(taxi):
    return {
        "id": str(taxi.id),
        "modelo": taxi.modelo,
        "matricula": taxi.matricula,
        "marca": taxi.marca,
        "ano_compra": taxi.ano_compra,
        "consumo_medio": str(taxi.consumo_medio),
        "tipo_motor": taxi.tipo_motor,
        "nivel_conforto": taxi.nivel_conforto,
        "estado": taxi.estado,
        "latitude": str(taxi.latitude) if taxi.latitude is not None else None,
        "longitude": str(taxi.longitude) if taxi.longitude is not None else None,
        "created_at": taxi.created_at,
        "updated_at": taxi.updated_at,
    }


def serialize_driver(driver):
    return {
        "id": driver.id,
        "name": getattr(driver, "name", None),
        "email": getattr(driver, "email", None),
        "phone_number": getattr(driver, "phone_number", None),
        "username": getattr(driver, "username", None),
    }


@api_view(["GET"])
def trips_driver_details(request):
    start_dt, end_dt = get_period(request)

    driver_id = request.GET.get("driver_id")
    metric = request.GET.get("metric", "trips")

    if not driver_id:
        return Response(
            {"success": False, "message": "driver_id é obrigatório"},
            status=400
        )

    duration_expr = ExpressionWrapper(
        F("end_date") - F("start_date"),
        output_field=DurationField()
    )

    trips = Trip.objects.filter(
        start_date__gte=start_dt,
        start_date__lte=end_dt,
        status_trip="finished",
        driver_id=driver_id,
    ).annotate(duration=duration_expr)

    if metric == "hours":
        trips = trips.order_by("-duration")
    elif metric == "kms":
        trips = trips.order_by("-n_kms")
    else:
        trips = trips.order_by("-start_date")

    return Response({
        "success": True,
        "driver_id": driver_id,
        "metric": metric,
        "trips": [serialize_trip(trip) for trip in trips]
    })


@api_view(["GET"])
def trips_taxi_details(request):
    start_dt, end_dt = get_period(request)

    taxi_id = request.GET.get("taxi_id")
    metric = request.GET.get("metric", "trips")

    if not taxi_id:
        return Response(
            {"success": False, "message": "taxi_id é obrigatório"},
            status=400
        )

    duration_expr = ExpressionWrapper(
        F("end_date") - F("start_date"),
        output_field=DurationField()
    )

    trips = Trip.objects.filter(
        start_date__gte=start_dt,
        start_date__lte=end_dt,
        status_trip="finished",
        taxi_id=taxi_id,
    ).annotate(duration=duration_expr)

    if metric == "hours":
        trips = trips.order_by("-duration")
    elif metric == "kms":
        trips = trips.order_by("-n_kms")
    else:
        trips = trips.order_by("-start_date")

    return Response({
        "success": True,
        "taxi_id": taxi_id,
        "metric": metric,
        "trips": [serialize_trip(trip) for trip in trips]
    })


@api_view(["GET"])
def trip_detail(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)

    return Response({
        "success": True,
        "trip": serialize_trip(trip)
    })


@api_view(["GET"])
def driver_detail(request, driver_id):
    driver = get_object_or_404(Driver, id=driver_id)

    return Response({
        "success": True,
        "driver": serialize_driver(driver)
    })


@api_view(["GET"])
def taxi_detail(request, taxi_id):
    taxi = get_object_or_404(Taxi, id=taxi_id)

    return Response({
        "success": True,
        "taxi": serialize_taxi(taxi)
    })


@api_view(["GET"])
def billing_summary(request):
    start_dt, end_dt = get_period(request)

    invoices = Invoice.objects.filter(data__gte=start_dt, data__lte=end_dt)

    total = invoices.aggregate(total_euros=Sum("price"))

    return Response({
        "success": True,
        "total_euros": str(total["total_euros"] or Decimal("0")),
    })


@api_view(["GET"])
def billing_by_client(request):
    start_dt, end_dt = get_period(request)

    rows = Invoice.objects.filter(
        data__gte=start_dt,
        data__lte=end_dt,
    ).values(
        "trip__client_id"
    ).annotate(
        total_euros=Sum("price"),
        total_invoices=Count("id")
    ).order_by("-total_euros")

    return Response({
        "success": True,
        "clients": [
            {
                "client_id": str(row["trip__client_id"]),
                "total_euros": str(row["total_euros"] or Decimal("0")),
                "total_invoices": row["total_invoices"],
            }
            for row in rows
        ]
    })


#USER STORY 16
@api_view(["GET"])
def refuel_summary(request):
    start_dt, end_dt = get_period(request)

    duration_expr = ExpressionWrapper(
        F("data_fim") - F("data_inicio"),
        output_field=DurationField()
    )

    refuels = Refuel.objects.filter(
        data_inicio__gte=start_dt,
        data_inicio__lte=end_dt,
    ).annotate(duration=duration_expr)

    total = refuels.aggregate(
        total_euros=Sum("euros_pagos"),
        total_duration=Sum("duration"),
    )

    return Response({
        "success": True,
        "total_euros": str(total["total_euros"] or Decimal("0")),
        "total_hours": duration_hours(total["total_duration"]),
    })

#USER STORY 16
@api_view(["GET"])
def refuel_by_motor_type(request):
    start_dt, end_dt = get_period(request)

    rows = Refuel.objects.filter(
        data_inicio__gte=start_dt,
        data_inicio__lte=end_dt,
    ).values(
        "taxi__tipo_motor"
    ).annotate(
        total_euros=Sum("euros_pagos"),
        total_refuels=Count("id")
    ).order_by("-total_euros")

    return Response({
        "success": True,
        "motor_types": [
            {
                "tipo_motor": row["taxi__tipo_motor"],
                "total_euros": str(row["total_euros"] or Decimal("0")),
                "total_refuels": row["total_refuels"],
            }
            for row in rows
        ]
    })