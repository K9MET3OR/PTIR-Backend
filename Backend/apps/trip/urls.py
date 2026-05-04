from django.urls import path

from . import views

urlpatterns = [
    path('', views.listar_trips),
    path('register/', views.registar_trip),
    path('register', views.registar_trip),
    path('<uuid:id_trip>/', views.gerir_trip),
    path('<uuid:id_trip>', views.gerir_trip),
    path('<uuid:pk>/accept/', views.accept_trip),
    path('<uuid:pk>/accept', views.accept_trip),
    path('<uuid:pk>/reject/', views.reject_trip),
    path('<uuid:pk>/reject', views.reject_trip),
    path('<uuid:pk>/finish/', views.finish_trip),
    path('<uuid:pk>/finish', views.finish_trip),
    path('pagamento/create/', views.criar_pagamento),
    path('pagamento/create', views.criar_pagamento),
    path('pagamento/confirm/', views.confirmar_pagamento),
    path('pagamento/confirm', views.confirmar_pagamento),
]
