from django.urls import path
from . import views

urlpatterns = [
    path("refuel/summary", views.refuel_summary),
    path("refuel/by-motor-type", views.refuel_by_motor_type),
]