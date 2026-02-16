"""
URL configuration for JEPCO Grid Stability Orchestrator.
"""

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.risk import ui_views

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Authentication
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # UI Views
    path('', ui_views.dashboard, name='dashboard'),
    path('workorders/', ui_views.work_orders_view, name='work_orders'),

    # API endpoints
    path('api/assets/', include('apps.assets.urls')),
    path('api/telemetry/', include('apps.telemetry.urls')),
    path('api/forecasting/', include('apps.forecasting.urls')),
    path('api/risk/', include('apps.risk.urls')),
    path('api/plans/', include('apps.planning.urls')),
    path('api/ops/', include('apps.ops.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
