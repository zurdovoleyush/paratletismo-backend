from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('paratletismo_core.users.urls')),
    path('api/config/', include('paratletismo_core.config.urls')),
    path('api/tournaments/', include('paratletismo_core.tournaments.urls')),
    path('api/competitions/', include('paratletismo_core.competitions.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
