"""
LLM API tracking models for JEPCO Grid.

Logs all Claude API calls for audit, debugging, and cost tracking.
"""

from django.db import models


class LLMAPILog(models.Model):
    """
    Log of Claude API calls for audit and debugging.

    Tracks every LLM invocation with input, output, and performance metrics.
    """

    # When and what
    created_at = models.DateTimeField(auto_now_add=True)
    operation_type = models.CharField(
        max_length=50,
        default='plan_enhancement',
        help_text="Type of operation (e.g., plan_enhancement, explanation_generation)"
    )

    # Input data
    input_data = models.JSONField(
        help_text="Input sent to LLM (plan_data, etc.)"
    )

    # Output data
    output_data = models.JSONField(
        null=True,
        blank=True,
        help_text="LLM response (executive_summary, steps, etc.)"
    )

    # Status
    STATUS_CHOICES = [
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('FALLBACK', 'Used Template Fallback')
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES
    )

    error_message = models.TextField(
        blank=True,
        help_text="Error message if failed"
    )

    # Performance metrics
    tokens_used = models.IntegerField(
        null=True,
        blank=True,
        help_text="Total tokens consumed (if available from API)"
    )

    response_time_ms = models.IntegerField(
        null=True,
        blank=True,
        help_text="API response time in milliseconds"
    )

    # Model info
    model_used = models.CharField(
        max_length=100,
        default='claude-sonnet-4-5-20250929'
    )

    # Link to related object (if any)
    related_plan_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="MitigationPlan ID if this log is for plan enhancement"
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        return f"LLM Log {self.id}: {self.operation_type} - {self.status} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
