from django.urls import path
from . import views

urlpatterns = [
    path('registo-motorista', views.registo_motorista),
]
