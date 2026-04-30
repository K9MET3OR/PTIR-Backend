from django.urls import path

from . import views

urlpatterns = [
    path('', views.create_user),
    path('login', views.login),
    path('<uuid:id>/', views.get_user),
    path('<uuid:id>/update/', views.update_user),
    path('<uuid:id>/delete/', views.delete_user),
]