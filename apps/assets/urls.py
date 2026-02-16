"""
URL configuration for Assets app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router and register viewsets
router = DefaultRouter()
router.register(r'substations', views.SubstationViewSet, basename='substation')
router.register(r'feeders', views.FeederViewSet, basename='feeder')
router.register(r'transformers', views.TransformerViewSet, basename='transformer')
router.register(r'switches', views.SwitchViewSet, basename='switch')
router.register(r'topology-links', views.TopologyLinkViewSet, basename='topologylink')

urlpatterns = [
    path('', include(router.urls)),
]
