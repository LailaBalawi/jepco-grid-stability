from django.contrib import admin
from django.utils import timezone
from .models import WorkOrder, AuditLog


@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    """Admin interface for Work Orders."""

    list_display = [
        'wo_number',
        'area',
        'assigned_team',
        'priority',
        'status',
        'created_at',
        'is_overdue'
    ]

    list_filter = [
        'status',
        'priority',
        'created_at',
        'assigned_team'
    ]

    search_fields = [
        'wo_number',
        'area',
        'assigned_team',
        'steps_text'
    ]

    readonly_fields = [
        'wo_number',
        'created_at',
        'started_at',
        'completed_at',
        'is_overdue'
    ]

    fieldsets = (
        ('Work Order Information', {
            'fields': (
                'wo_number',
                'plan',
                'created_at',
                'priority'
            )
        }),
        ('Assignment', {
            'fields': (
                'assigned_team',
                'area'
            )
        }),
        ('Work Details', {
            'fields': (
                'steps_text',
            )
        }),
        ('Status', {
            'fields': (
                'status',
                'started_at',
                'completed_at',
                'is_overdue'
            )
        }),
        ('Outcome', {
            'fields': (
                'outcome_notes',
                'attachments'
            )
        })
    )

    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    def save_model(self, request, obj, form, change):
        """Auto-populate timestamps based on status changes."""
        if 'status' in form.changed_data:
            if obj.status == 'IN_PROGRESS' and not obj.started_at:
                obj.started_at = timezone.now()
            elif obj.status == 'COMPLETED' and not obj.completed_at:
                obj.completed_at = timezone.now()

        super().save_model(request, obj, form, change)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin interface for Audit Logs."""

    list_display = [
        'timestamp',
        'action_type',
        'user',
        'success',
        'ip_address'
    ]

    list_filter = [
        'action_type',
        'success',
        'timestamp',
        'user'
    ]

    search_fields = [
        'action_type',
        'user__username',
        'details_json',
        'error_message'
    ]

    readonly_fields = [
        'timestamp',
        'action_type',
        'user',
        'content_type',
        'object_id',
        'details_json',
        'ip_address',
        'user_agent',
        'success',
        'error_message'
    ]

    fieldsets = (
        ('Event Information', {
            'fields': (
                'timestamp',
                'action_type',
                'user',
                'success'
            )
        }),
        ('Related Object', {
            'fields': (
                'content_type',
                'object_id'
            )
        }),
        ('Details', {
            'fields': (
                'details_json',
                'error_message'
            ),
            'classes': ('collapse',)
        }),
        ('Network Information', {
            'fields': (
                'ip_address',
                'user_agent'
            ),
            'classes': ('collapse',)
        })
    )

    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']

    def has_add_permission(self, request):
        """Audit logs cannot be manually created."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Audit logs cannot be deleted (compliance requirement)."""
        return False
