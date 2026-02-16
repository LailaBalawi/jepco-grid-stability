"""
URL configuration for Ops app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WorkOrderViewSet, AuditLogViewSet

router = DefaultRouter()
router.register(r'workorders', WorkOrderViewSet, basename='workorder')
router.register(r'audit', AuditLogViewSet, basename='audit')

urlpatterns = [
    path('', include(router.urls)),
]
