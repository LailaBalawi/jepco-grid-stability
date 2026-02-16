from django.contrib import admin
from django.utils import timezone
from .models import MitigationPlan


@admin.register(MitigationPlan)
class MitigationPlanAdmin(admin.ModelAdmin):
    """
    Admin interface for Mitigation Plan model.

    Allows operators to review, approve, and track mitigation plans.
    """

    list_display = [
        'id',
        'transformer_display',
        'transfer_display',
        'status',
        'expected_risk_after',
        'risk_reduction',
        'generated_at',
        'approved_by'
    ]

    list_filter = [
        'status',
        'generated_at',
        'approved_at'
    ]

    search_fields = [
        'assessment__transformer__name',
        'plan_json'
    ]

    readonly_fields = [
        'generated_at',
        'plan_json',
        'expected_risk_after',
        'expected_load_reduction_kw',
        'risk_reduction'
    ]

    fieldsets = (
        ('Plan Information', {
            'fields': (
                'assessment',
                'generated_at',
                'status'
            )
        }),
        ('Simulation Results', {
            'fields': (
                'plan_json',
                'expected_risk_after',
                'expected_load_reduction_kw',
                'risk_reduction'
            )
        }),
        ('Generated Instructions', {
            'fields': (
                'executive_summary',
                'operator_steps',
                'field_checklist',
                'rollback_steps',
                'assumptions',
                'llm_confidence'
            ),
            'classes': ('collapse',)
        }),
        ('Approval', {
            'fields': (
                'approved_by',
                'approved_at',
                'rejection_reason'
            )
        }),
        ('Execution', {
            'fields': (
                'executed_by',
                'executed_at',
                'execution_notes'
            )
        })
    )

    date_hierarchy = 'generated_at'
    ordering = ['-generated_at']

    def transformer_display(self, obj):
        """Display transformer name."""
        return obj.assessment.transformer.name
    transformer_display.short_description = 'Transformer'

    def transfer_display(self, obj):
        """Display transfer details."""
        from_name = obj.plan_json.get('from_transformer_name', '?')
        to_name = obj.plan_json.get('to_transformer_name', '?')
        transfer_kw = obj.plan_json.get('transfer_kw', 0)
        return f"{from_name} => {to_name} ({transfer_kw} kW)"
    transfer_display.short_description = 'Transfer'

    def save_model(self, request, obj, form, change):
        """Auto-populate approval fields when status changes."""
        if 'status' in form.changed_data:
            if obj.status == 'APPROVED' and not obj.approved_at:
                obj.approved_by = request.user
                obj.approved_at = timezone.now()
            elif obj.status == 'EXECUTED' and not obj.executed_at:
                obj.executed_by = request.user
                obj.executed_at = timezone.now()

        super().save_model(request, obj, form, change)
