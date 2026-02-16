"""
Serializers for Ops app.
"""

from rest_framework import serializers
from .models import WorkOrder, AuditLog


class WorkOrderSerializer(serializers.ModelSerializer):
    """Serializer for WorkOrder model."""

    plan_detail = serializers.SerializerMethodField()
    transformer_name = serializers.SerializerMethodField()
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = WorkOrder
        fields = [
            'id',
            'wo_number',
            'plan',
            'plan_detail',
            'transformer_name',
            'created_at',
            'assigned_team',
            'steps_text',
            'area',
            'priority',
            'status',
            'started_at',
            'completed_at',
            'outcome_notes',
            'attachments',
            'is_overdue'
        ]
        read_only_fields = [
            'wo_number',
            'created_at',
            'is_overdue'
        ]

    def get_plan_detail(self, obj):
        """Get basic plan information."""
        return {
            'id': obj.plan.id,
            'transfer_summary': obj.plan.plan_json.get('from_transformer_name', '') + ' => ' + obj.plan.plan_json.get('to_transformer_name', ''),
            'transfer_kw': obj.plan.plan_json.get('transfer_kw', 0),
            'risk_reduction': obj.plan.risk_reduction
        }

    def get_transformer_name(self, obj):
        """Get transformer name from plan."""
        return obj.plan.assessment.transformer.name


class WorkOrderListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing work orders."""

    transformer_name = serializers.CharField(source='plan.assessment.transformer.name', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = WorkOrder
        fields = [
            'id',
            'wo_number',
            'transformer_name',
            'area',
            'assigned_team',
            'priority',
            'status',
            'created_at',
            'is_overdue'
        ]


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for AuditLog model."""

    user_display = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            'id',
            'timestamp',
            'action_type',
            'user',
            'user_display',
            'content_type',
            'object_id',
            'details_json',
            'ip_address',
            'user_agent',
            'success',
            'error_message'
        ]
        read_only_fields = '__all__'

    def get_user_display(self, obj):
        """Get user display name."""
        return obj.user.username if obj.user else 'System'
