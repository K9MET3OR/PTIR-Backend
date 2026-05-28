from django.urls import path
from . import views

urlpatterns = [
    path("trips/summary", views.trips_summary),
    path("trips/by-driver", views.trips_by_driver),
    path("trips/by-taxi", views.trips_by_taxi),
    path("billing/summary", views.billing_summary),
    path("billing/by-client", views.billing_by_client),
    path("refuel/summary", views.refuel_summary),
    path("refuel/by-motor-type", views.refuel_by_motor_type),
]