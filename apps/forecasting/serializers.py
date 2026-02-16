"""
Serializers for Forecasting app.
"""

from rest_framework import serializers
from .models import LoadForecast
from apps.assets.serializers import TransformerSerializer


class LoadForecastSerializer(serializers.ModelSerializer):
    """
    Serializer for LoadForecast model.

    Includes full transformer details and all prediction data.
    """

    transformer_detail = TransformerSerializer(source='transformer', read_only=True)

    class Meta:
        model = LoadForecast
        fields = [
            'id',
            'transformer',
            'transformer_detail',
            'forecast_generated_at',
            'forecast_horizon_hours',
            'predictions',
            'peak_predicted_kw',
            'peak_predicted_pct',
            'peak_time',
            'algorithm',
            'metadata'
        ]
        read_only_fields = ['forecast_generated_at']


class LoadForecastListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing forecasts.

    Excludes predictions array to reduce payload size.
    """

    transformer_name = serializers.CharField(source='transformer.name', read_only=True)
    feeder_name = serializers.CharField(source='transformer.feeder.name', read_only=True)
    substation_name = serializers.CharField(source='transformer.feeder.substation.name', read_only=True)

    class Meta:
        model = LoadForecast
        fields = [
            'id',
            'transformer',
            'transformer_name',
            'feeder_name',
            'substation_name',
            'forecast_generated_at',
            'forecast_horizon_hours',
            'peak_predicted_kw',
            'peak_predicted_pct',
            'peak_time',
            'algorithm'
        ]
