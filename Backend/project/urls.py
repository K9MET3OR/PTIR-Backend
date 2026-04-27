from django.urls import path, include

urlpatterns = [
    path('api/user/', include('apps.user.urls')),
    path('api/driver/', include('apps.user.driver.urls')),
    path('api/taxi/', include('apps.taxi.urls')),
    path('api/trip/', include('apps.trip.urls')),
    path('api/shift/', include('apps.shift.urls')),
    path('api/invoice/', include('apps.invoice.urls')),
    path('api/refuel/', include('apps.refuel.urls')),
    path('api/client/', include('apps.user.client.urls')),
    path('auth/', include('apps.user.auth_urls')),
]