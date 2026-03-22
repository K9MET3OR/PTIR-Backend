from django.urls import path
from . import views

urlpatterns = [
    path('', views.create_user),
    path('login/', views.login),
    path('<uuid:id>/', views.delete_user),
]