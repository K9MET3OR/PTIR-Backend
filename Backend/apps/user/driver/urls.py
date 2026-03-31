from django.urls import path
from . import views

urlpatterns = [
    path('registo-motorista', views.registo_motorista),
    path('login', views.login_nif),
    path('motorista/', views.listar_motoristas),
    path('motorista/<uuid:id_motorista>/', views.gerir_motorista),
]