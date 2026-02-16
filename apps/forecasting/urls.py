"""
URL configuration for Forecasting app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LoadForecastViewSet

router = DefaultRouter()
router.register(r'forecasts', LoadForecastViewSet, basename='forecast')

urlpatterns = [
    path('', include(router.urls)),
]
