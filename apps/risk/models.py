"""
Risk Assessment models for JEPCO Grid Stability Orchestrator.

Stores risk assessments based on load forecasts with transparent,
explainable scoring methodology.
"""

from django.db import models
from decimal import Decimal


class RiskAssessment(models.Model):
    """
    Risk assessment for a transformer based on load forecast.

    Combines multiple risk factors:
    - Overload risk (0-1): based on peak % of rated capacity
    - Thermal risk (0-1): based on temperature if available
    - Cascading risk (0-1): based on neighbor transformer status

    Final risk score: 0.0 (safe) to 1.0 (critical)
    """

    transformer = models.ForeignKey(
        'assets.Transformer',
        on_delete=models.CASCADE,
        related_name='risk_assessments'
    )

    forecast = models.ForeignKey(
        'forecasting.LoadForecast',
        on_delete=models.CASCADE,
        related_name='risk_assessments'
    )

    assessed_at = models.DateTimeField(auto_now_add=True)

    # Time window for this risk assessment
    time_window_start = models.DateTimeField()
    time_window_end = models.DateTimeField()

    # Overall risk score (0.000-1.000)
    risk_score = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        help_text="Overall risk score: 0.000 (safe) to 1.000 (critical)"
    )

    # Peak load metrics
    overload_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Predicted peak load as % of rated capacity"
    )

    # Forecast confidence
    confidence = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        help_text="Confidence in this assessment (0.0-1.0)"
    )

    # Risk components (stored for transparency)
    risk_components = models.JSONField(
        default=dict,
        help_text="Breakdown of risk components: {overload: 0.x, thermal: 0.x, cascading: 0.x}"
    )

    # Human-readable explanation
    reasons_json = models.JSONField(
        default=dict,
        help_text="Structured explanation of why this transformer is at risk"
    )

    # Risk level classification
    RISK_LEVELS = [
        ('LOW', 'Low Risk (0.0-0.3)'),
        ('MEDIUM', 'Medium Risk (0.3-0.7)'),
        ('HIGH', 'High Risk (0.7-1.0)')
    ]

    risk_level = models.CharField(
        max_length=10,
        choices=RISK_LEVELS,
        db_index=True
    )

    class Meta:
        ordering = ['-risk_score', '-assessed_at']
        indexes = [
            models.Index(fields=['-risk_score', '-assessed_at']),
            models.Index(fields=['transformer', '-assessed_at']),
        ]

    def __str__(self):
        return f"{self.transformer.name} - Risk {self.risk_score} ({self.risk_level}) - {self.assessed_at.strftime('%Y-%m-%d %H:%M')}"

    def save(self, *args, **kwargs):
        """Auto-calculate risk_level based on risk_score."""
        if self.risk_level is None or self.risk_level == '':
            score = float(self.risk_score)
            if score < 0.3:
                self.risk_level = 'LOW'
            elif score < 0.7:
                self.risk_level = 'MEDIUM'
            else:
                self.risk_level = 'HIGH'
        super().save(*args, **kwargs)

    @property
    def is_high_risk(self):
        """Quick check if this is a high-risk assessment."""
        return self.risk_level == 'HIGH'

    @property
    def requires_action(self):
        """Determine if this assessment requires operator action."""
        return float(self.risk_score) >= 0.7 or float(self.overload_pct) > 100.0
