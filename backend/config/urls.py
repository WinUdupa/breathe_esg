from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.clients.urls')),
    path('api/ingestion/', include('apps.ingestion.urls')),
    path('api/review/', include('apps.review.urls')),
    path('api/admin/', include('apps.review.admin_urls')),
    path('api/reporting/', include('apps.reporting.urls')),
    path('api/audit/', include('apps.audit.urls')),
    path('api/periods/', include('apps.clients.period_urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
