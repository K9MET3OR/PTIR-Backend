from django.urls import path

from . import views

urlpatterns = [
    path('', views.listar_taxis),
    path('register', views.registo_taxi),

    path('pricing', views.pricing_config),
    path('pricing/simular', views.simular_preco_viagem),

    path('calcucate-travel-cost', views.calcular_valor_viagem),
    path('calcular-preco-com-conforto', views.calcular_preco_com_conforto),

    path('<uuid:id_taxi>/remove', views.apagar_taxi),
    path('<uuid:id_taxi>/estado', views.atualizar_estado_taxi),
    path('<uuid:id_taxi>/localizacao', views.atualizar_localizacao_taxi),
    path('<uuid:id_taxi>', views.gerir_taxi),
]