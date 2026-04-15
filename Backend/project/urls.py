from django.urls import path, include

urlpatterns = [
    path('api/user/', include('apps.user.urls')),
    path('api/taxis/', include('apps.taxi.urls')),
    path('api/trip/', include('apps.trip.urls')),
    path('api/motoristas/', include('apps.user.driver.urls')),
    path('api/clientes/', include('apps.user.client.urls')),
    path('auth/', include('apps.user.auth_urls')),
]