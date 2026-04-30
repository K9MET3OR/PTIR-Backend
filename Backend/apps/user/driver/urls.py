from django.urls import path
from . import views

urlpatterns = [
    path('', views.listar_motoristas),
    path('register', views.registo_motorista),
    path('login', views.login_nif),
    path('localidade/<str:codigo_postal>', views.get_localidade),
    path('<uuid:id_motorista>', views.gerir_motorista),
    path('<uuid:id_motorista>/estado', views.atualizar_estado),
]