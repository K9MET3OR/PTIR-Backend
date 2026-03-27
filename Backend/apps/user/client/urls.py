from django.urls import path

from . import views

urlpatterns = [
	path('registo', views.registo_client),
	path('login', views.login_client_nif),
]
