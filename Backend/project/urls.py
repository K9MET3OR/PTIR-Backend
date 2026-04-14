from django.urls import path, include

urlpatterns = [
    path('api/user/', include('apps.user.urls')),
    path('api/motoristas/', include('apps.user.driver.urls')),
    path('api/taxis/', include('apps.taxi.urls')),
    path('auth/', include('apps.user.auth_urls')),
]