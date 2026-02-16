"""
Serializers for Planning app.
"""

from rest_framework import serializers
from .models import MitigationPlan
from apps.risk.serializers import RiskAssessmentSerializer


class MitigationPlanSerializer(serializers.ModelSerializer):
    """
    Full serializer for MitigationPlan model.

    Includes complete assessment details and LLM-generated instructions.
    """

    assessment_detail = RiskAssessmentSerializer(source='assessment', read_only=True)
    risk_reduction = serializers.SerializerMethodField()
    transformer_name = serializers.SerializerMethodField()

    class Meta:
        model = MitigationPlan
        fields = [
            'id',
            'assessment',
            'assessment_detail',
            'transformer_name',
            'generated_at',
            'plan_json',
            'expected_risk_after',
            'expected_load_reduction_kw',
            'risk_reduction',
            'executive_summary',
            'operator_steps',
            'field_checklist',
            'rollback_steps',
            'assumptions',
            'llm_confidence',
            'status',
            'approved_by',
            'approved_at',
            'rejection_reason',
            'executed_at',
            'executed_by',
            'execution_notes',
            'is_approved',
            'is_executed'
        ]
        read_only_fields = [
            'generated_at',
            'is_approved',
            'is_executed',
            'risk_reduction'
        ]

    def get_risk_reduction(self, obj):
        """Calculate risk reduction."""
        return obj.risk_reduction

    def get_transformer_name(self, obj):
        """Get transformer name from assessment."""
        return obj.assessment.transformer.name


class MitigationPlanListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing mitigation plans.

    Excludes detailed instructions to reduce payload size.
    """

    transformer_name = serializers.CharField(source='assessment.transformer.name', read_only=True)
    risk_before = serializers.SerializerMethodField()
    risk_reduction = serializers.SerializerMethodField()
    transfer_summary = serializers.SerializerMethodField()

    class Meta:
        model = MitigationPlan
        fields = [
            'id',
            'transformer_name',
            'generated_at',
            'status',
            'risk_before',
            'expected_risk_after',
            'risk_reduction',
            'expected_load_reduction_kw',
            'transfer_summary',
            'is_approved',
            'is_executed'
        ]

    def get_risk_before(self, obj):
        """Get original risk score."""
        return obj.assessment.risk_score

    def get_risk_reduction(self, obj):
        """Calculate risk reduction."""
        return obj.risk_reduction

    def get_transfer_summary(self, obj):
        """Get transfer summary from plan_json."""
        from_name = obj.plan_json.get('from_transformer_name', '?')
        to_name = obj.plan_json.get('to_transformer_name', '?')
        transfer_kw = obj.plan_json.get('transfer_kw', 0)
        return f"{from_name} => {to_name} ({transfer_kw:.0f} kW)"


class PlanApprovalSerializer(serializers.Serializer):
    """
    Serializer for plan approval/rejection actions.
    """

    action = serializers.ChoiceField(choices=['approve', 'reject'])
    rejection_reason = serializers.CharField(required=False, allow_blank=True)
