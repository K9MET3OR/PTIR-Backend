from django.urls import path, include

urlpatterns = [
    path('api/user/', include('apps.user.urls')),
    path('auth/', include('apps.user.auth_urls')),
]