"""
Models for JEPCO Grid Forecasting.

This module contains models for storing load forecasts (predictions).
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.assets.models import Transformer


class LoadForecast(models.Model):
    """
    Stores a load forecast for a transformer.

    Forecasts predict transformer load 24-72 hours ahead using time-series analysis.
    Each forecast contains predictions for every hour in the forecast horizon.
    """
    transformer = models.ForeignKey(
        Transformer, on_delete=models.CASCADE, related_name='forecasts',
        help_text="Transformer this forecast is for"
    )
    forecast_generated_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this forecast was generated"
    )
    forecast_horizon_hours = models.IntegerField(
        default=72,
        validators=[MinValueValidator(1), MaxValueValidator(168)],
        help_text="How many hours ahead this forecast predicts (default 72h)"
    )
    predictions = models.JSONField(
        help_text="Array of predictions: [{timestamp, predicted_kw, confidence}, ...]"
    )
    peak_predicted_kw = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Maximum predicted load in the forecast period"
    )
    peak_predicted_pct = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Peak load as percentage of rated capacity"
    )
    peak_time = models.DateTimeField(
        help_text="When the peak load is predicted to occur"
    )
    algorithm = models.CharField(
        max_length=50, default='baseline',
        help_text="Forecasting algorithm used (baseline, prophet, lstm, etc.)"
    )
    metadata = models.JSONField(
        default=dict, blank=True,
        help_text="Additional metadata (MAE, RMSE, parameters, etc.)"
    )

    class Meta:
        ordering = ['-forecast_generated_at']
        verbose_name = "Load Forecast"
        verbose_name_plural = "Load Forecasts"
        indexes = [
            models.Index(fields=['transformer', '-forecast_generated_at']),
        ]

    def __str__(self):
        return (f"Forecast for {self.transformer.name} - "
                f"Peak: {self.peak_predicted_kw} kW ({self.peak_predicted_pct}%) "
                f"at {self.peak_time:%Y-%m-%d %H:%M}")
