from django.urls import path
from . import views

urlpatterns = [
    path('', views.listar_shifts),
    path('register', views.registar_shift),
    path('taxis-available/', views.taxis_disponiveis),
    path('driver/<uuid:driver_id>', views.listar_shifts_driver),
    path('<int:id_shift>/finish', views.terminar_shift),
    path('<int:id_shift>/cancelar/', views.cancelar_shift),
    path('<int:id_shift>', views.gerir_shift),

    path('registar/', views.registar_shift),
    path('taxis-disponiveis/', views.taxis_disponiveis),
    path('driver/<uuid:driver_id>/', views.listar_shifts_driver),
    path('<int:id_shift>/terminar/', views.terminar_shift),
    path('<int:id_shift>/', views.gerir_shift),
]