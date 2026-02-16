"""
DRF Serializers for Assets app.
"""

from rest_framework import serializers
from .models import Substation, Feeder, Transformer, Switch, TopologyLink


class SubstationSerializer(serializers.ModelSerializer):
    """Serializer for Substation model"""
    feeder_count = serializers.IntegerField(source='feeders.count', read_only=True)

    class Meta:
        model = Substation
        fields = ['id', 'name', 'region', 'latitude', 'longitude', 'feeder_count', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class FeederSerializer(serializers.ModelSerializer):
    """Serializer for Feeder model"""
    substation_name = serializers.CharField(source='substation.name', read_only=True)
    transformer_count = serializers.IntegerField(source='transformers.count', read_only=True)

    class Meta:
        model = Feeder
        fields = [
            'id', 'substation', 'substation_name', 'name', 'voltage_level',
            'rated_capacity_kw', 'transformer_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class TransformerSerializer(serializers.ModelSerializer):
    """Serializer for Transformer model"""
    feeder_name = serializers.CharField(source='feeder.name', read_only=True)
    substation_name = serializers.CharField(source='feeder.substation.name', read_only=True)
    rated_kw = serializers.FloatField(read_only=True)

    class Meta:
        model = Transformer
        fields = [
            'id', 'feeder', 'feeder_name', 'substation_name', 'name', 'rated_kva', 'rated_kw',
            'max_load_pct', 'cooling_type', 'install_year', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['rated_kw', 'created_at', 'updated_at']


class SwitchSerializer(serializers.ModelSerializer):
    """Serializer for Switch model"""
    feeder_name = serializers.CharField(source='feeder.name', read_only=True)

    class Meta:
        model = Switch
        fields = [
            'id', 'feeder', 'feeder_name', 'name', 'switch_type', 'location',
            'status', 'last_operated', 'created_at', 'updated_at'
        ]
        read_only_fields = ['last_operated', 'created_at', 'updated_at']


class TopologyLinkSerializer(serializers.ModelSerializer):
    """Serializer for TopologyLink model"""
    from_transformer_name = serializers.CharField(source='from_transformer.name', read_only=True)
    to_transformer_name = serializers.CharField(source='to_transformer.name', read_only=True)
    switch_name = serializers.CharField(source='switch.name', read_only=True, allow_null=True)

    class Meta:
        model = TopologyLink
        fields = [
            'id', 'from_transformer', 'from_transformer_name',
            'to_transformer', 'to_transformer_name',
            'link_type', 'max_transfer_kw', 'switch', 'switch_name',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class TransformerTopologySerializer(serializers.ModelSerializer):
    """
    Detailed serializer for transformer with topology information.
    Used for topology view.
    """
    feeder = FeederSerializer(read_only=True)
    outgoing_links = TopologyLinkSerializer(many=True, read_only=True)
    incoming_links = TopologyLinkSerializer(many=True, read_only=True)
    neighbors = serializers.SerializerMethodField()

    class Meta:
        model = Transformer
        fields = [
            'id', 'name', 'rated_kva', 'rated_kw', 'max_load_pct',
            'feeder', 'outgoing_links', 'incoming_links', 'neighbors'
        ]

    def get_neighbors(self, obj):
        """Get all neighbor transformers via topology links"""
        neighbor_ids = set()

        # Add transformers from outgoing links
        for link in obj.outgoing_links.filter(is_active=True):
            neighbor_ids.add(link.to_transformer.id)

        # Add transformers from incoming links
        for link in obj.incoming_links.filter(is_active=True):
            neighbor_ids.add(link.from_transformer.id)

        # Get neighbor transformer objects
        neighbors = Transformer.objects.filter(id__in=neighbor_ids)

        return TransformerSerializer(neighbors, many=True).data
