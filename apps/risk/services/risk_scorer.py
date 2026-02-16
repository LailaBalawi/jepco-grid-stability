"""
Risk Scoring Service for JEPCO Grid.

Implements transparent, explainable risk scoring methodology:
- Overload risk: based on predicted peak load vs capacity
- Thermal risk: based on temperature and transformer age
- Cascading risk: based on neighbor transformer status

Risk Score = 0.6 × overload + 0.2 × thermal + 0.2 × cascading
"""

from decimal import Decimal
from django.utils import timezone
from apps.risk.models import RiskAssessment
from apps.forecasting.models import LoadForecast
from apps.assets.models import TopologyLink
from apps.telemetry.models import TransformerLoad


class RiskScorer:
    """
    Calculate risk scores for transformers based on forecasts.

    This is a transparent, rule-based scoring system (not a black box).
    All scoring logic is documented and explainable.
    """

    # Weight factors for risk components
    OVERLOAD_WEIGHT = 0.6
    THERMAL_WEIGHT = 0.2
    CASCADING_WEIGHT = 0.2

    def score_transformer(self, transformer, forecast):
        """
        Generate risk assessment for a single transformer.

        Args:
            transformer (Transformer): Transformer instance
            forecast (LoadForecast): Load forecast for this transformer

        Returns:
            RiskAssessment: Saved risk assessment instance

        Raises:
            ValueError: If forecast data is incomplete
        """
        if not forecast.predictions:
            raise ValueError(f"Forecast for {transformer.name} has no predictions")

        # Calculate risk components
        overload_score = self._calculate_overload_score(forecast.peak_predicted_pct)
        thermal_score = self._calculate_thermal_score(forecast, transformer)
        cascading_score = self._calculate_cascading_score(transformer)

        # Weighted combination
        total_score = (
            self.OVERLOAD_WEIGHT * overload_score +
            self.THERMAL_WEIGHT * thermal_score +
            self.CASCADING_WEIGHT * cascading_score
        )

        # Generate human-readable reasons
        reasons = self._generate_reasons(
            transformer, forecast, overload_score, thermal_score, cascading_score
        )

        # Determine time window
        time_window_start = forecast.predictions[0]['timestamp'] if isinstance(forecast.predictions[0]['timestamp'], str) else forecast.predictions[0]['timestamp'].isoformat()
        time_window_end = forecast.predictions[-1]['timestamp'] if isinstance(forecast.predictions[-1]['timestamp'], str) else forecast.predictions[-1]['timestamp'].isoformat()

        # Parse timestamps if they are strings
        from datetime import datetime
        if isinstance(time_window_start, str):
            time_window_start = datetime.fromisoformat(time_window_start.replace('Z', '+00:00'))
        if isinstance(time_window_end, str):
            time_window_end = datetime.fromisoformat(time_window_end.replace('Z', '+00:00'))

        # Create assessment
        assessment = RiskAssessment(
            transformer=transformer,
            forecast=forecast,
            time_window_start=time_window_start,
            time_window_end=time_window_end,
            risk_score=round(Decimal(str(total_score)), 3),
            overload_pct=forecast.peak_predicted_pct,
            confidence=self._calculate_assessment_confidence(forecast),
            risk_components={
                'overload': round(overload_score, 3),
                'thermal': round(thermal_score, 3),
                'cascading': round(cascading_score, 3)
            },
            reasons_json=reasons
        )

        # Save to database
        assessment.save()

        return assessment

    def _calculate_overload_score(self, load_pct):
        """
        Calculate overload risk score based on predicted peak load percentage.

        Scoring logic:
        - load_pct <= 90%: 0.0 (safe operation)
        - load_pct 90-100%: scales from 0.3 to 0.7 (elevated risk)
        - load_pct > 100%: scales from 0.7 to 1.0 (critical risk)

        Args:
            load_pct (float): Predicted peak load as % of rated capacity

        Returns:
            float: Overload score (0.0-1.0)
        """
        load_pct = float(load_pct)

        if load_pct <= 90:
            return 0.0
        elif load_pct <= 100:
            # Linear scaling: 90% → 0.3, 100% → 0.7
            return 0.3 + ((load_pct - 90) * 0.04)
        else:
            # Linear scaling: 100% → 0.7, 120% → 1.0
            return min(0.7 + ((load_pct - 100) * 0.015), 1.0)

    def _calculate_thermal_score(self, forecast, transformer):
        """
        Calculate thermal risk score based on temperature and transformer age.

        Considers:
        - Ambient temperature (if available in forecast metadata)
        - Transformer age (older transformers more vulnerable to heat)
        - Cooling system type

        Args:
            forecast (LoadForecast): Load forecast
            transformer (Transformer): Transformer instance

        Returns:
            float: Thermal score (0.0-1.0)
        """
        # Get latest temperature reading
        latest_temp = None
        latest_reading = TransformerLoad.objects.filter(
            transformer=transformer,
            temp_c__isnull=False
        ).order_by('-timestamp').first()

        if latest_reading:
            latest_temp = float(latest_reading.temp_c)

        if not latest_temp:
            # No temperature data, use conservative estimate
            return 0.2

        # Base thermal risk from temperature
        # 25°C = 0.0, 30°C = 0.3, 35°C = 0.6, 40°C+ = 0.9
        if latest_temp <= 25:
            temp_score = 0.0
        elif latest_temp <= 30:
            temp_score = (latest_temp - 25) * 0.06  # 0.0-0.3
        elif latest_temp <= 35:
            temp_score = 0.3 + ((latest_temp - 30) * 0.06)  # 0.3-0.6
        elif latest_temp <= 40:
            temp_score = 0.6 + ((latest_temp - 35) * 0.06)  # 0.6-0.9
        else:
            temp_score = min(0.9 + ((latest_temp - 40) * 0.02), 1.0)

        # Adjust for transformer age
        current_year = timezone.now().year
        age = current_year - transformer.install_year

        if age > 25:
            age_factor = 1.3  # Old transformers more vulnerable
        elif age > 15:
            age_factor = 1.1
        else:
            age_factor = 1.0

        # Adjust for cooling type
        cooling_factor = 0.8 if transformer.cooling_type == 'ONAF' else 1.0  # ONAF is better

        final_score = min(temp_score * age_factor * cooling_factor, 1.0)

        return final_score

    def _calculate_cascading_score(self, transformer):
        """
        Calculate cascading risk score based on neighbor transformer status.

        Checks if neighbor transformers (via topology links) are also heavily loaded.
        If neighbors can't absorb load, cascading risk is higher.

        Args:
            transformer (Transformer): Transformer instance

        Returns:
            float: Cascading score (0.0-1.0)
        """
        # Get all neighbors via topology links
        outgoing_links = TopologyLink.objects.filter(
            from_transformer=transformer,
            is_active=True
        ).select_related('to_transformer')

        if not outgoing_links.exists():
            # Isolated transformer = higher risk (no load transfer options)
            return 0.5

        # Check load status of neighbors
        neighbors_overloaded = 0
        total_neighbors = 0

        for link in outgoing_links:
            neighbor = link.to_transformer
            total_neighbors += 1

            # Get latest load reading for neighbor
            latest = TransformerLoad.objects.filter(
                transformer=neighbor
            ).order_by('-timestamp').first()

            if latest and float(latest.load_pct) > 85:
                neighbors_overloaded += 1

        if total_neighbors == 0:
            return 0.5

        # Calculate cascading score
        overload_ratio = neighbors_overloaded / total_neighbors

        if overload_ratio == 0:
            return 0.0  # All neighbors have capacity
        elif overload_ratio < 0.5:
            return 0.3  # Some neighbors overloaded
        else:
            return 0.7  # Most/all neighbors overloaded

    def _calculate_assessment_confidence(self, forecast):
        """
        Calculate confidence in the risk assessment.

        Based on forecast confidence and data availability.

        Args:
            forecast (LoadForecast): Load forecast

        Returns:
            Decimal: Confidence score (0.0-1.0)
        """
        if not forecast.predictions:
            return Decimal('0.5')

        # Average confidence from forecast predictions
        confidences = [p['confidence'] for p in forecast.predictions]
        avg_confidence = sum(confidences) / len(confidences)

        return round(Decimal(str(avg_confidence)), 3)

    def _generate_reasons(self, transformer, forecast, overload_score, thermal_score, cascading_score):
        """
        Generate human-readable explanations for the risk score.

        Args:
            transformer (Transformer): Transformer instance
            forecast (LoadForecast): Load forecast
            overload_score (float): Overload component score
            thermal_score (float): Thermal component score
            cascading_score (float): Cascading component score

        Returns:
            dict: Structured reasons
        """
        reasons = {
            'primary': '',
            'bullets': [],
            'recommendations': []
        }

        # Determine primary reason (highest component)
        max_score = max(overload_score, thermal_score, cascading_score)

        if max_score == overload_score and overload_score > 0.5:
            reasons['primary'] = f"Predicted overload: {forecast.peak_predicted_pct}% of rated capacity"
            reasons['bullets'].append(
                f"Peak load predicted at {forecast.peak_time.strftime('%Y-%m-%d %H:%M')}"
            )
            if float(forecast.peak_predicted_pct) > 100:
                reasons['bullets'].append(
                    f"CRITICAL: Load exceeds transformer rating by {float(forecast.peak_predicted_pct) - 100:.1f}%"
                )
                reasons['recommendations'].append("Generate mitigation plan immediately")
            else:
                reasons['bullets'].append(
                    f"WARNING: Operating near capacity limit ({transformer.max_load_pct}%)"
                )
                reasons['recommendations'].append("Monitor closely and prepare contingency plan")

        elif max_score == thermal_score and thermal_score > 0.5:
            reasons['primary'] = "Elevated thermal risk"
            reasons['bullets'].append("High ambient temperature affecting transformer cooling")

            # Get age
            age = timezone.now().year - transformer.install_year
            if age > 25:
                reasons['bullets'].append(f"Transformer age: {age} years (aging equipment more vulnerable)")

            reasons['recommendations'].append("Consider load reduction during hot hours")
            reasons['recommendations'].append("Verify cooling system operation")

        elif max_score == cascading_score and cascading_score > 0.5:
            reasons['primary'] = "High cascading failure risk"
            reasons['bullets'].append("Neighbor transformers also heavily loaded")
            reasons['bullets'].append("Limited load transfer options available")
            reasons['recommendations'].append("Review regional load distribution")
            reasons['recommendations'].append("Consider demand response program")

        else:
            reasons['primary'] = "Normal operation with elevated monitoring"
            reasons['bullets'].append("Multiple minor risk factors detected")
            reasons['recommendations'].append("Continue standard monitoring procedures")

        return reasons


class BulkRiskScorer:
    """
    Generate risk assessments for multiple transformers efficiently.
    """

    def __init__(self):
        self.scorer = RiskScorer()

    def score_all_transformers(self, transformers=None):
        """
        Generate risk assessments for all (or specified) transformers.

        Args:
            transformers: QuerySet or list of transformers (default: all active)

        Returns:
            dict: {
                'successful': list of RiskAssessment instances,
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
                # Get latest forecast for this transformer
                forecast = LoadForecast.objects.filter(
                    transformer=transformer
                ).order_by('-forecast_generated_at').first()

                if not forecast:
                    raise ValueError(f"No forecast available for {transformer.name}")

                # Generate risk assessment
                assessment = self.scorer.score_transformer(transformer, forecast)
                successful.append(assessment)

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
