"""
API views for Assets app.
"""

from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Substation, Feeder, Transformer, Switch, TopologyLink
from .serializers import (
    SubstationSerializer, FeederSerializer, TransformerSerializer,
    SwitchSerializer, TopologyLinkSerializer, TransformerTopologySerializer
)


class SubstationViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Substations.

    Provides CRUD operations for substations.
    """
    queryset = Substation.objects.all()
    serializer_class = SubstationSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'region']
    ordering_fields = ['name', 'region', 'created_at']
    ordering = ['name']


class FeederViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Feeders.

    Provides CRUD operations for feeders with filtering by substation.
    """
    queryset = Feeder.objects.select_related('substation').all()
    serializer_class = FeederSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['substation', 'voltage_level']
    search_fields = ['name', 'substation__name']
    ordering_fields = ['name', 'voltage_level', 'rated_capacity_kw']
    ordering = ['substation__name', 'name']


class TransformerViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Transformers.

    Provides CRUD operations and topology information for transformers.
    """
    queryset = Transformer.objects.select_related(
        'feeder', 'feeder__substation'
    ).prefetch_related(
        'outgoing_links', 'incoming_links'
    ).all()
    serializer_class = TransformerSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['feeder', 'feeder__substation', 'is_active', 'cooling_type']
    search_fields = ['name', 'feeder__name', 'feeder__substation__name']
    ordering_fields = ['name', 'rated_kva', 'install_year']
    ordering = ['name']

    @action(detail=True, methods=['get'])
    def topology(self, request, pk=None):
        """
        Get topology information for a specific transformer.

        Returns the transformer with all its connections (neighbors via topology links).
        """
        transformer = self.get_object()
        serializer = TransformerTopologySerializer(transformer)
        return Response(serializer.data)


class SwitchViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Switches.

    Provides CRUD operations for switches with filtering and search.
    """
    queryset = Switch.objects.select_related('feeder').all()
    serializer_class = SwitchSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['feeder', 'switch_type', 'status']
    search_fields = ['name', 'location']
    ordering_fields = ['name', 'last_operated']
    ordering = ['name']


class TopologyLinkViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Topology Links.

    Provides CRUD operations for topology links (connections between transformers).
    Admin-only for create/update/delete to prevent unauthorized topology changes.
    """
    queryset = TopologyLink.objects.select_related(
        'from_transformer', 'to_transformer', 'switch'
    ).all()
    serializer_class = TopologyLinkSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['from_transformer', 'to_transformer', 'link_type', 'is_active']
    search_fields = ['from_transformer__name', 'to_transformer__name']
    ordering_fields = ['from_transformer__name', 'to_transformer__name', 'max_transfer_kw']
    ordering = ['from_transformer__name', 'to_transformer__name']

    def get_permissions(self):
        """
        Restrict write operations to admin users only.
        """
        from rest_framework.permissions import IsAdminUser, IsAuthenticated

        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]
