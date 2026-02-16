"""
Mitigation Planning models for JEPCO Grid.

Stores simulated load transfer plans with LLM-generated operator instructions.
"""

from django.db import models
from decimal import Decimal


class MitigationPlan(models.Model):
    """
    Mitigation plan for reducing transformer overload risk.

    Contains:
    - Simulated load transfer scenarios
    - Expected risk reduction
    - LLM-generated operator instructions
    - Safety checklists and rollback procedures
    """

    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('EXECUTED', 'Executed')
    ]

    # Link to risk assessment that triggered this plan
    assessment = models.ForeignKey(
        'risk.RiskAssessment',
        on_delete=models.CASCADE,
        related_name='mitigation_plans'
    )

    generated_at = models.DateTimeField(auto_now_add=True)

    # Simulation data (structured JSON)
    plan_json = models.JSONField(
        help_text="Structured transfer details: {from_transformer, to_transformer, transfer_kw, switch_id, ...}"
    )

    # Expected outcome
    expected_risk_after = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        help_text="Predicted risk score after plan execution"
    )

    expected_load_reduction_kw = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Expected load reduction in kW"
    )

    # LLM-generated content (will be populated by Phase 7)
    executive_summary = models.TextField(
        blank=True,
        help_text="Plain-language summary of the plan"
    )

    operator_steps = models.JSONField(
        default=list,
        help_text="Step-by-step instructions for control room"
    )

    field_checklist = models.JSONField(
        default=list,
        help_text="Safety checklist for field crew"
    )

    rollback_steps = models.JSONField(
        default=list,
        help_text="Emergency reversion procedures"
    )

    assumptions = models.JSONField(
        default=list,
        help_text="Key assumptions and uncertainties"
    )

    llm_confidence = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        default=Decimal('0.0'),
        help_text="LLM confidence in generated plan (0.0-1.0)"
    )

    # Approval tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        db_index=True
    )

    approved_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_plans'
    )

    approved_at = models.DateTimeField(null=True, blank=True)

    rejection_reason = models.TextField(blank=True)

    # Execution tracking
    executed_at = models.DateTimeField(null=True, blank=True)
    executed_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='executed_plans'
    )

    execution_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['status', '-generated_at']),
            models.Index(fields=['assessment', '-generated_at']),
        ]

    def __str__(self):
        from_trans = self.plan_json.get('from_transformer', 'Unknown')
        to_trans = self.plan_json.get('to_transformer', 'Unknown')
        return f"Plan {self.id}: {from_trans} => {to_trans} ({self.status})"

    @property
    def risk_reduction(self):
        """Calculate expected risk reduction."""
        if self.assessment:
            return float(self.assessment.risk_score) - float(self.expected_risk_after)
        return 0.0

    @property
    def is_approved(self):
        """Check if plan is approved."""
        return self.status == 'APPROVED'

    @property
    def is_executed(self):
        """Check if plan has been executed."""
        return self.status == 'EXECUTED'
