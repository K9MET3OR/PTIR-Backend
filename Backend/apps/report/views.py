from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum, Count, F, ExpressionWrapper, DurationField
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.trip.models import Trip
from apps.invoice.models import Invoice
from apps.refuel.models import Refuel


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