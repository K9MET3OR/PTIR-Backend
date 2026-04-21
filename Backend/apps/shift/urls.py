from django.urls import path
from . import views

urlpatterns = [
    path('', views.listar_shifts),
    path('criar', views.registar_shift),
    path('<uuid:id_shift>/', views.gerir_shift),
]
