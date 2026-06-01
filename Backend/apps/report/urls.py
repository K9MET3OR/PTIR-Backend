from django.urls import path
from . import views

urlpatterns = [
    path("trips/summary", views.trips_summary),
    path("trips/by-driver", views.trips_by_driver),
    path("trips/by-taxi", views.trips_by_taxi),

    path("trips/driver-details", views.trips_driver_details),
    path("trips/taxi-details", views.trips_taxi_details),
    path("trips/detail/<int:trip_id>", views.trip_detail),
    path("drivers/detail/<int:driver_id>", views.driver_detail),
    path("taxis/detail/<uuid:taxi_id>", views.taxi_detail),

    path("billing/summary", views.billing_summary),
    path("billing/by-client", views.billing_by_client),

    path("billing/client-details", views.billing_client_details),
    path("clients/detail/<str:client_id>", views.client_detail),

    path("refuel/summary", views.refuel_summary),
    path("refuel/by-motor-type", views.refuel_by_motor_type),

    path("refuel/by-taxi", views.refuel_by_taxi)
]