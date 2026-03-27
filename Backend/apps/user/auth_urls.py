from django.urls import include, path

urlpatterns = [
    path('', include('apps.user.driver.urls')),
    path('admin/', include('apps.user.admin.urls')),
    path('client/', include('apps.user.client.urls')),
    path('taxi/', include('apps.taxi.urls')),
]
