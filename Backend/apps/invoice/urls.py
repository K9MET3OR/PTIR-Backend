from django.urls import path
from . import views

urlpatterns = [
    path('', views.listar_invoices),
    path("register/", views.register_invoice),
    path("register", views.register_invoice),
    path("driver/<uuid:driver_id>/", views.listar_invoices_driver),
    path("driver/<uuid:driver_id>", views.listar_invoices_driver),
]