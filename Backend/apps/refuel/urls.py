from django.urls import path
from . import views

urlpatterns = [
    path("register", views.register_refuel),
    path("taxi/<uuid:taxi_id>", views.listar_refuels_taxi),
    path("<int:id_refuel>", views.gerir_refuel),
]