from django.urls import path
from . import views

urlpatterns = [
    path('taxis-available', views.taxis_disponiveis),
    path('register', views.registar_shift),
    path('shift/<uuid:driver_id>', views.listar_shifts_driver),
    path('<uuid:id_shift>/finish', views.terminar_shift),
    path('<uuid:id_shift>', views.gerir_shift),
    path('', views.listar_shifts),
]
