from django.urls import path

from . import views

urlpatterns = [
    path('', views.listar_clients),
    path('registo', views.registo_client),
    path('login', views.login_client_nif),
    path('<uuid:id_client>/', views.gerir_client),
]