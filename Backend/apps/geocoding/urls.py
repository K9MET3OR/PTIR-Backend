from django.urls import path
from .views import geocoding_search

urlpatterns = [
    path("search", geocoding_search),
]