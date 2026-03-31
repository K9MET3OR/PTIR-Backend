from django.urls import path

from . import views

urlpatterns = [
    path('', views.listar_admins),
    path('registo', views.registo_admin),
    path('login', views.login_admin_nif),
    path('<uuid:id_admin>/', views.gerir_admin),
]