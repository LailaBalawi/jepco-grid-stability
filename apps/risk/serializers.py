"""
Serializers for Risk app.
"""

from rest_framework import serializers
from .models import RiskAssessment
from apps.assets.serializers import TransformerSerializer
from apps.forecasting.serializers import LoadForecastSerializer


class RiskAssessmentSerializer(serializers.ModelSerializer):
    """
    Full serializer for RiskAssessment model.

    Includes complete transformer and forecast details.
    """

    transformer_detail = TransformerSerializer(source='transformer', read_only=True)
    forecast_detail = LoadForecastSerializer(source='forecast', read_only=True)

    class Meta:
        model = RiskAssessment
        fields = [
            'id',
            'transformer',
            'transformer_detail',
            'forecast',
            'forecast_detail',
            'assessed_at',
            'time_window_start',
            'time_window_end',
            'risk_score',
            'risk_level',
            'overload_pct',
            'confidence',
            'risk_components',
            'reasons_json',
            'is_high_risk',
            'requires_action'
        ]
        read_only_fields = [
            'assessed_at',
            'risk_score',
            'risk_level',
            'risk_components',
            'reasons_json',
            'is_high_risk',
            'requires_action'
        ]


class RiskAssessmentListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing risk assessments.

    Excludes nested details to reduce payload size.
    """

    transformer_name = serializers.CharField(source='transformer.name', read_only=True)
    feeder_name = serializers.CharField(source='transformer.feeder.name', read_only=True)
    substation_name = serializers.CharField(source='transformer.feeder.substation.name', read_only=True)
    peak_time = serializers.DateTimeField(source='forecast.peak_time', read_only=True)
    primary_reason = serializers.SerializerMethodField()

    class Meta:
        model = RiskAssessment
        fields = [
            'id',
            'transformer',
            'transformer_name',
            'feeder_name',
            'substation_name',
            'assessed_at',
            'time_window_start',
            'time_window_end',
            'risk_score',
            'risk_level',
            'overload_pct',
            'confidence',
            'peak_time',
            'primary_reason',
            'is_high_risk',
            'requires_action'
        ]

    def get_primary_reason(self, obj):
        """Extract primary reason from reasons_json."""
        return obj.reasons_json.get('primary', 'No reason specified')


class RiskExplanationSerializer(serializers.Serializer):
    """
    Serializer for detailed risk explanation.

    Used for chart-ready breakdown of risk components.
    """

    transformer_name = serializers.CharField()
    risk_score = serializers.DecimalField(max_digits=4, decimal_places=3)
    risk_level = serializers.CharField()

    # Component scores
    overload_component = serializers.DecimalField(max_digits=4, decimal_places=3)
    thermal_component = serializers.DecimalField(max_digits=4, decimal_places=3)
    cascading_component = serializers.DecimalField(max_digits=4, decimal_places=3)

    # Weighted contributions
    overload_contribution = serializers.DecimalField(max_digits=4, decimal_places=3)
    thermal_contribution = serializers.DecimalField(max_digits=4, decimal_places=3)
    cascading_contribution = serializers.DecimalField(max_digits=4, decimal_places=3)

    # Explanation
    reasons = serializers.DictField()
