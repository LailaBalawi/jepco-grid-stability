"""
URL configuration for Risk app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RiskAssessmentViewSet

router = DefaultRouter()
router.register(r'assessments', RiskAssessmentViewSet, basename='assessment')

urlpatterns = [
    path('', include(router.urls)),
]
