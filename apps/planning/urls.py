"""
URL configuration for Planning app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MitigationPlanViewSet

router = DefaultRouter()
router.register(r'plans', MitigationPlanViewSet, basename='plan')

urlpatterns = [
    path('', include(router.urls)),
]
