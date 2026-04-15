from django.urls import path

from . import views

urlpatterns = [
    path('registar/', views.registar_trip),
    path('listar/', views.listar_trips),
    path('<uuid:id_trip>/', views.gerir_trip),
    path('<uuid:pk>/accept/', views.accept_trip),
    path('<uuid:pk>/reject/', views.reject_trip),
    path('<uuid:pk>/finish/', views.finish_trip),
    path('pagamento/criar/', views.criar_pagamento),
    path('pagamento/confirmar/', views.confirmar_pagamento),
]
