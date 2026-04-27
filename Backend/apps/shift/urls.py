from django.urls import path
from . import views

urlpatterns = [
    path('taxis-disponiveis/', views.taxis_disponiveis),
    path('registar', views.registar_shift),
    path('driver/<int:driver_id>/', views.listar_shifts_driver),
    path('<uuid:id_shift>/', views.gerir_shift),
    path('', views.listar_shifts),
]
