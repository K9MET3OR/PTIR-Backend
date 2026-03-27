from django.urls import path

from . import views

urlpatterns = [
	path('registo', views.registo_admin),
	path('login', views.login_admin_nif),
]
