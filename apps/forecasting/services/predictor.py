"""
Load Forecasting Service for JEPCO Grid.

Implements baseline time-series forecasting using:
- Rolling average by hour-of-day
- Seasonal patterns (weekday vs weekend)
- Temperature correlation
"""

from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from django.db.models import Avg, Max
import numpy as np

from apps.telemetry.models import TransformerLoad
from apps.forecasting.models import LoadForecast


class LoadForecaster:
    """
    Baseline load forecasting using hourly patterns and seasonality.

    This is a transparent, explainable forecasting method that:
    1. Calculates average load per hour-of-day from historical data
    2. Applies day-of-week adjustments (weekends typically 15% lower)
    3. Incorporates temperature correlation
    4. Provides confidence scores based on historical variance
    """

    def __init__(self, lookback_days=7):
        """
        Initialize forecaster.

        Args:
            lookback_days: Number of days of historical data to use (default 7)
        """
        self.lookback_days = lookback_days

    def forecast(self, transformer, hours_ahead=72):
        """
        Generate load forecast for a transformer.

        Args:
            transformer: Transformer instance to forecast
            hours_ahead: Number of hours to predict (default 72)

        Returns:
            LoadForecast instance (not saved to database)

        Raises:
            ValueError: If insufficient historical data
        """
        # Get historical data
        cutoff_time = timezone.now() - timedelta(days=self.lookback_days)
        historical_data = TransformerLoad.objects.filter(
            transformer=transformer,
            timestamp__gte=cutoff_time
        ).order_by('timestamp')

        if historical_data.count() < 24:
            raise ValueError(
                f"Insufficient data for {transformer.name}. "
                f"Need at least 24 hours, have {historical_data.count()}"
            )

        # Calculate hourly load patterns
        hourly_patterns = self._calculate_hourly_patterns(historical_data)

        # Generate predictions
        predictions = []
        now = timezone.now()
        peak_kw = 0
        peak_time = now
        peak_pct = 0

        for hour_offset in range(hours_ahead):
            target_time = now + timedelta(hours=hour_offset)
            hour_of_day = target_time.hour
            day_of_week = target_time.weekday()  # 0=Monday, 6=Sunday

            # Get base prediction from hourly pattern
            predicted_kw = hourly_patterns.get(hour_of_day, transformer.rated_kw * 0.7)

            # Apply day-of-week adjustment
            if day_of_week in [5, 6]:  # Weekend
                predicted_kw *= 0.85  # 15% reduction on weekends

            # Temperature adjustment (if historical temp data exists)
            temp_factor = self._estimate_temperature_factor(target_time, historical_data)
            predicted_kw *= temp_factor

            # Calculate confidence (higher variance = lower confidence)
            confidence = self._calculate_confidence(hour_of_day, historical_data)

            # Track peak
            predicted_pct = (predicted_kw / transformer.rated_kw) * 100
            if predicted_kw > peak_kw:
                peak_kw = predicted_kw
                peak_time = target_time
                peak_pct = predicted_pct

            predictions.append({
                'timestamp': target_time.isoformat(),
                'predicted_kw': round(predicted_kw, 2),
                'predicted_pct': round(predicted_pct, 2),
                'confidence': round(confidence, 3)
            })

        # Create forecast object (not saved)
        forecast = LoadForecast(
            transformer=transformer,
            forecast_horizon_hours=hours_ahead,
            predictions=predictions,
            peak_predicted_kw=round(peak_kw, 2),
            peak_predicted_pct=round(peak_pct, 2),
            peak_time=peak_time,
            algorithm='baseline',
            metadata={
                'lookback_days': self.lookback_days,
                'historical_records': historical_data.count(),
                'method': 'hourly_average_with_seasonality'
            }
        )

        return forecast

    def _calculate_hourly_patterns(self, historical_data):
        """
        Calculate average load for each hour of day (0-23).

        Returns:
            dict: {hour: average_kw}
        """
        hourly_averages = {}

        for hour in range(24):
            hour_data = [
                float(reading.load_kw)
                for reading in historical_data
                if reading.timestamp.hour == hour
            ]

            if hour_data:
                hourly_averages[hour] = np.mean(hour_data)
            else:
                # Fallback: use overall average
                all_loads = [float(r.load_kw) for r in historical_data]
                hourly_averages[hour] = np.mean(all_loads) if all_loads else 0

        return hourly_averages

    def _estimate_temperature_factor(self, target_time, historical_data):
        """
        Estimate temperature impact on load.

        For demo purposes, we apply a simple heuristic:
        - Midday/afternoon (12-18h): higher temp effect (1.05-1.15)
        - Morning/evening: moderate effect (0.95-1.05)
        - Night: lower effect (0.90-1.00)
        """
        hour = target_time.hour

        # Check if we have temperature data
        temps = [r.temp_c for r in historical_data if r.temp_c]
        has_temp_data = len(temps) > 0

        if not has_temp_data:
            # No temperature data, use time-of-day heuristic
            if 12 <= hour <= 18:
                return 1.10  # Assume higher load during hot hours
            elif 6 <= hour <= 11 or 19 <= hour <= 22:
                return 1.0
            else:
                return 0.95  # Lower load at night

        # If we have temp data, use a more sophisticated approach
        avg_temp = np.mean([float(t) for t in temps])

        # Estimate temperature for target time (simple hourly pattern)
        if 12 <= hour <= 16:
            estimated_temp = avg_temp + 3  # Hottest hours
        elif 17 <= hour <= 20:
            estimated_temp = avg_temp + 1
        elif 0 <= hour <= 6:
            estimated_temp = avg_temp - 3  # Coolest hours
        else:
            estimated_temp = avg_temp

        # Temperature impact: 1% load increase per degree above 25°C
        if estimated_temp > 25:
            return 1.0 + ((estimated_temp - 25) * 0.01)
        else:
            return 1.0

    def _calculate_confidence(self, hour_of_day, historical_data):
        """
        Calculate forecast confidence based on historical variance.

        Lower variance at this hour = higher confidence
        More data = higher confidence

        Returns:
            float: Confidence score 0.0-1.0
        """
        # Get load values for this hour
        hour_loads = [
            float(reading.load_kw)
            for reading in historical_data
            if reading.timestamp.hour == hour_of_day
        ]

        if not hour_loads or len(hour_loads) < 3:
            return 0.60  # Low confidence with insufficient data

        # Calculate coefficient of variation (CV)
        mean_load = np.mean(hour_loads)
        std_load = np.std(hour_loads)

        if mean_load == 0:
            return 0.70

        cv = std_load / mean_load

        # Convert CV to confidence (lower CV = higher confidence)
        # CV < 0.05 → confidence 0.95
        # CV = 0.15 → confidence 0.85
        # CV > 0.30 → confidence 0.70
        confidence = max(0.70, min(0.95, 1.0 - cv))

        # Adjust for sample size
        sample_size_factor = min(1.0, len(hour_loads) / 7)  # Full confidence with 7+ samples
        confidence *= sample_size_factor

        return confidence


class BulkForecaster:
    """
    Generate forecasts for multiple transformers efficiently.
    """

    def __init__(self, lookback_days=7, hours_ahead=72):
        self.forecaster = LoadForecaster(lookback_days=lookback_days)
        self.hours_ahead = hours_ahead

    def forecast_all_transformers(self, transformers=None, save=True):
        """
        Generate forecasts for all (or specified) transformers.

        Args:
            transformers: QuerySet or list of transformers (default: all active)
            save: Whether to save forecasts to database (default True)

        Returns:
            dict: {
                'successful': list of LoadForecast instances,
                'failed': list of {transformer, error} dicts
            }
        """
        from apps.assets.models import Transformer

        if transformers is None:
            transformers = Transformer.objects.filter(is_active=True)

        successful = []
        failed = []

        for transformer in transformers:
            try:
                forecast = self.forecaster.forecast(transformer, self.hours_ahead)

                if save:
                    forecast.save()

                successful.append(forecast)

            except Exception as e:
                failed.append({
                    'transformer': transformer,
                    'error': str(e)
                })

        return {
            'successful': successful,
            'failed': failed,
            'total_attempted': len(transformers),
            'success_count': len(successful),
            'failure_count': len(failed)
        }
