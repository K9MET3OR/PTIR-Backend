from django.urls import path
from . import views

urlpatterns = [
    path('', views.listar_invoices),
    path("register", views.register_invoice),
    path("driver/<uuid:driver_id>", views.listar_invoices_driver),
    path("<int:id_invoice>", views.gerir_invoice),
]