from django.urls import path

from . import views

urlpatterns = [
    path('registo-taxi', views.registo_taxi),
    path('calcular-valor-viagem', views.calcular_valor_viagem),
    path('', views.listar_taxis),
    path('<uuid:id_taxi>/apagar', views.apagar_taxi),
    path('<uuid:id_taxi>/', views.gerir_taxi),
]
