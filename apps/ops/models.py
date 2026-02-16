"""
Operations models for JEPCO Grid.

Handles work orders and comprehensive audit logging for all system actions.
"""

from django.db import models
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


class WorkOrder(models.Model):
    """
    Work Order for field execution of mitigation plans.

    Converts approved plans into field-executable tasks with tracking.
    """

    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled')
    ]

    # Link to mitigation plan
    plan = models.ForeignKey(
        'planning.MitigationPlan',
        on_delete=models.CASCADE,
        related_name='work_orders'
    )

    # Auto-generated work order number (WO-YYYY-####)
    wo_number = models.CharField(
        max_length=20,
        unique=True,
        help_text="Auto-generated: WO-2026-0001"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    # Assignment
    assigned_team = models.CharField(
        max_length=100,
        help_text="Field crew/team name"
    )

    # Work details
    steps_text = models.TextField(
        help_text="Operator steps from mitigation plan"
    )

    area = models.CharField(
        max_length=100,
        help_text="Geographic area (substation/region)"
    )

    priority = models.CharField(
        max_length=20,
        choices=[
            ('LOW', 'Low'),
            ('MEDIUM', 'Medium'),
            ('HIGH', 'High'),
            ('CRITICAL', 'Critical')
        ],
        default='MEDIUM'
    )

    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='OPEN',
        db_index=True
    )

    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Outcome
    outcome_notes = models.TextField(
        blank=True,
        help_text="Field crew notes after execution"
    )

    attachments = models.FileField(
        upload_to='workorders/',
        null=True,
        blank=True,
        help_text="Photos, diagrams, etc."
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['wo_number']),
        ]

    def __str__(self):
        return f"{self.wo_number} - {self.area} ({self.status})"

    def save(self, *args, **kwargs):
        """Auto-generate WO number if not set."""
        if not self.wo_number:
            self.wo_number = self._generate_wo_number()
        super().save(*args, **kwargs)

    def _generate_wo_number(self):
        """
        Generate auto-incrementing work order number.

        Format: WO-YYYY-####
        """
        year = timezone.now().year
        last_wo = WorkOrder.objects.filter(
            wo_number__startswith=f'WO-{year}'
        ).order_by('-wo_number').first()

        if last_wo:
            last_num = int(last_wo.wo_number.split('-')[-1])
            new_num = last_num + 1
        else:
            new_num = 1

        return f'WO-{year}-{new_num:04d}'

    @property
    def is_overdue(self):
        """Check if work order is overdue (open > 24 hours)."""
        if self.status in ['COMPLETED', 'CANCELLED']:
            return False
        hours_open = (timezone.now() - self.created_at).total_seconds() / 3600
        return hours_open > 24


class AuditLog(models.Model):
    """
    Comprehensive audit trail for all system actions.

    Logs every significant operation for compliance and debugging.
    """

    ACTION_TYPES = [
        ('FORECAST_RUN', 'Forecast Run'),
        ('RISK_ASSESS', 'Risk Assessment'),
        ('PLAN_GEN', 'Plan Generated'),
        ('PLAN_APPROVE', 'Plan Approved'),
        ('PLAN_REJECT', 'Plan Rejected'),
        ('WO_CREATE', 'Work Order Created'),
        ('WO_START', 'Work Order Started'),
        ('WO_COMPLETE', 'Work Order Completed'),
        ('WO_CANCEL', 'Work Order Cancelled'),
        ('DATA_UPLOAD', 'Data Upload'),
        ('USER_LOGIN', 'User Login'),
        ('USER_LOGOUT', 'User Logout'),
        ('CONFIG_CHANGE', 'Configuration Change')
    ]

    # What happened
    action_type = models.CharField(
        max_length=20,
        choices=ACTION_TYPES,
        db_index=True
    )

    # When and who
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # What was affected (generic foreign key for flexibility)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    # Details
    details_json = models.JSONField(
        default=dict,
        help_text="Structured details about the action"
    )

    # Network info
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)

    # Outcome
    success = models.BooleanField(
        default=True,
        help_text="Whether the action completed successfully"
    )

    error_message = models.TextField(
        blank=True,
        help_text="Error details if action failed"
    )

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['action_type', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
        ]

    def __str__(self):
        user_str = self.user.username if self.user else 'System'
        return f"{user_str} - {self.action_type} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
