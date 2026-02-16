"""
Mitigation Simulation Service for JEPCO Grid.

Generates and ranks load transfer plans to reduce transformer overload risk.

Algorithm:
1. Find all neighbors via TopologyLink
2. Calculate available capacity on each neighbor
3. Simulate transfer scenarios
4. Rank by post-mitigation risk score
"""

from decimal import Decimal
from django.utils import timezone
from apps.planning.models import MitigationPlan
from apps.risk.models import RiskAssessment
from apps.risk.services.risk_scorer import RiskScorer
from apps.assets.models import TopologyLink, Transformer
from apps.telemetry.models import TransformerLoad
from apps.forecasting.models import LoadForecast


class MitigationSimulator:
    """
    Generate load transfer plans to mitigate transformer overload risk.

    This is a simulation engine that evaluates different transfer scenarios
    and ranks them by expected risk reduction.
    """

    def __init__(self, safety_margin=0.8, max_transfer_pct=0.3):
        """
        Initialize simulator with safety parameters.

        Args:
            safety_margin (float): Only use 80% of available capacity (default 0.8)
            max_transfer_pct (float): Maximum % of transformer load to transfer (default 0.3)
        """
        self.safety_margin = safety_margin
        self.max_transfer_pct = max_transfer_pct
        self.risk_scorer = RiskScorer()

    def generate_plans(self, risk_assessment, max_plans=3):
        """
        Generate mitigation plans for a risky transformer.

        Args:
            risk_assessment (RiskAssessment): Risk assessment triggering mitigation
            max_plans (int): Maximum number of plans to generate (default 3)

        Returns:
            list: List of MitigationPlan instances (unsaved)

        Raises:
            ValueError: If no viable plans can be generated
        """
        transformer = risk_assessment.transformer
        forecast = risk_assessment.forecast

        # Calculate how much load needs to be transferred
        overload_kw = self._calculate_overload_kw(risk_assessment)

        if overload_kw <= 0:
            raise ValueError(f"Transformer {transformer.name} is not overloaded")

        # Find all neighbors via topology links
        neighbors = self._get_neighbors(transformer)

        if not neighbors:
            raise ValueError(f"Transformer {transformer.name} has no topology neighbors for load transfer")

        # Generate candidate plans
        candidate_plans = []

        for neighbor_info in neighbors:
            neighbor = neighbor_info['transformer']
            link = neighbor_info['link']

            # Calculate available capacity on neighbor
            available_kw = self._get_available_capacity(neighbor, risk_assessment.time_window_start)

            if available_kw < 50:  # Minimum viable transfer
                continue

            # Calculate transfer amount (don't exceed overload OR neighbor capacity)
            max_transfer_by_link = float(link.max_transfer_kw)
            max_transfer_by_capacity = available_kw * self.safety_margin
            max_transfer_by_source = float(forecast.peak_predicted_kw) * self.max_transfer_pct

            transfer_kw = min(
                overload_kw,
                max_transfer_by_link,
                max_transfer_by_capacity,
                max_transfer_by_source
            )

            if transfer_kw < 50:  # Not enough to make a difference
                continue

            # Simulate post-transfer state
            simulated_risk = self._simulate_transfer(
                transformer, neighbor, transfer_kw, forecast
            )

            # Calculate risk reduction
            risk_reduction = float(risk_assessment.risk_score) - simulated_risk

            # Create plan data
            plan_data = {
                'from_transformer': transformer.id,
                'from_transformer_name': transformer.name,
                'to_transformer': neighbor.id,
                'to_transformer_name': neighbor.name,
                'transfer_kw': round(transfer_kw, 2),
                'switch_id': link.switch.id if link.switch else None,
                'switch_name': link.switch.name if link.switch else 'direct',
                'link_capacity_kw': float(link.max_transfer_kw),
                'risk_before': float(risk_assessment.risk_score),
                'risk_after': simulated_risk,
                'risk_reduction': round(risk_reduction, 3),
                'expected_operations': 1 if link.switch else 0,
                'load_before_pct': float(forecast.peak_predicted_pct),
                'load_after_pct': round(
                    ((float(forecast.peak_predicted_kw) - transfer_kw) / float(transformer.rated_kw)) * 100,
                    2
                )
            }

            # Create MitigationPlan instance (not saved yet)
            plan = MitigationPlan(
                assessment=risk_assessment,
                plan_json=plan_data,
                expected_risk_after=Decimal(str(simulated_risk)),
                expected_load_reduction_kw=Decimal(str(transfer_kw)),
                # LLM fields will be populated in Phase 7
                executive_summary=f"Transfer {transfer_kw:.0f} kW from {transformer.name} to {neighbor.name}",
                operator_steps=[
                    f"1. Verify {link.switch.name if link.switch else 'tie line'} is operational",
                    f"2. Close {link.switch.name if link.switch else 'connection'} to transfer load",
                    f"3. Monitor both transformers for 10 minutes",
                    f"4. Verify {transformer.name} load drops below 90%"
                ],
                field_checklist=[
                    "PPE verification",
                    "Lockout/tagout procedures followed",
                    "Communication equipment functional"
                ],
                rollback_steps=[
                    f"1. If voltage deviation > 1.05 pu, reopen {link.switch.name if link.switch else 'connection'}",
                    "2. Notify control room immediately",
                    "3. Record outcome in work order notes"
                ],
                assumptions=[
                    f"Forecast error margin ±6%",
                    f"Weather conditions remain stable",
                    f"No concurrent outages in area"
                ],
                llm_confidence=Decimal('0.0')  # Will be updated in Phase 7
            )

            candidate_plans.append(plan)

        if not candidate_plans:
            raise ValueError(f"No viable mitigation plans for {transformer.name} (neighbors at capacity)")

        # Rank by risk reduction (descending)
        ranked_plans = sorted(
            candidate_plans,
            key=lambda p: p.plan_json['risk_reduction'],
            reverse=True
        )

        # Return top N plans
        return ranked_plans[:max_plans]

    def _calculate_overload_kw(self, risk_assessment):
        """
        Calculate how much load must be reduced to reach safe levels.

        Target: 90% of rated capacity

        Args:
            risk_assessment (RiskAssessment): Risk assessment

        Returns:
            float: kW to transfer
        """
        transformer = risk_assessment.transformer
        forecast = risk_assessment.forecast

        peak_kw = float(forecast.peak_predicted_kw)
        safe_kw = float(transformer.rated_kw) * (float(transformer.max_load_pct) / 100.0)

        overload_kw = peak_kw - safe_kw

        return max(0, overload_kw)

    def _get_neighbors(self, transformer):
        """
        Get all neighbor transformers connected via active topology links.

        Args:
            transformer (Transformer): Source transformer

        Returns:
            list: List of {transformer, link} dicts
        """
        outgoing_links = TopologyLink.objects.filter(
            from_transformer=transformer,
            is_active=True
        ).select_related('to_transformer', 'switch')

        neighbors = []
        for link in outgoing_links:
            neighbors.append({
                'transformer': link.to_transformer,
                'link': link
            })

        return neighbors

    def _get_available_capacity(self, transformer, time_window_start):
        """
        Calculate available capacity on a transformer.

        Available = Rated kW - Current/Predicted Load

        Args:
            transformer (Transformer): Transformer to check
            time_window_start (datetime): Time of interest

        Returns:
            float: Available capacity in kW
        """
        # Get latest load reading or forecast
        latest_load = TransformerLoad.objects.filter(
            transformer=transformer
        ).order_by('-timestamp').first()

        if latest_load:
            current_load_kw = float(latest_load.load_kw)
        else:
            # Use forecast if available
            forecast = LoadForecast.objects.filter(
                transformer=transformer
            ).order_by('-forecast_generated_at').first()

            if forecast:
                current_load_kw = float(forecast.peak_predicted_kw)
            else:
                # Conservative estimate: assume 70% load
                current_load_kw = float(transformer.rated_kw) * 0.7

        # Calculate available capacity
        safe_capacity = float(transformer.rated_kw) * (float(transformer.max_load_pct) / 100.0)
        available_kw = safe_capacity - current_load_kw

        return max(0, available_kw)

    def _simulate_transfer(self, from_transformer, to_transformer, transfer_kw, forecast):
        """
        Simulate post-transfer risk score.

        Creates a hypothetical forecast with reduced load and recalculates risk.

        Args:
            from_transformer (Transformer): Source transformer
            to_transformer (Transformer): Destination transformer
            transfer_kw (float): Amount to transfer
            forecast (LoadForecast): Original forecast

        Returns:
            float: Simulated risk score after transfer
        """
        # Create a hypothetical forecast with reduced load
        new_peak_kw = float(forecast.peak_predicted_kw) - transfer_kw
        new_peak_pct = (new_peak_kw / float(from_transformer.rated_kw)) * 100

        # Simple risk estimation without creating new objects
        # Use the same scoring logic as RiskScorer
        overload_score = self.risk_scorer._calculate_overload_score(new_peak_pct)

        # Thermal risk remains similar (conservative assumption)
        thermal_score = self.risk_scorer._calculate_thermal_score(forecast, from_transformer)

        # Cascading risk might increase if neighbor becomes loaded
        # For simplicity, use current cascading score (could be improved)
        cascading_score = self.risk_scorer._calculate_cascading_score(from_transformer)

        # Weighted combination
        simulated_risk = (
            0.6 * overload_score +
            0.2 * thermal_score +
            0.2 * cascading_score
        )

        return round(simulated_risk, 3)


class BulkMitigationPlanner:
    """
    Generate mitigation plans for multiple high-risk transformers.
    """

    def __init__(self):
        self.simulator = MitigationSimulator()

    def plan_all_high_risk(self, min_risk_score=0.7):
        """
        Generate plans for all high-risk transformers.

        Args:
            min_risk_score (float): Minimum risk score to trigger planning (default 0.7)

        Returns:
            dict: {
                'successful': list of MitigationPlan lists,
                'failed': list of {assessment, error} dicts
            }
        """
        # Get all high-risk assessments
        high_risk_assessments = RiskAssessment.objects.filter(
            risk_score__gte=min_risk_score
        ).select_related('transformer', 'forecast').order_by('-risk_score')

        successful = []
        failed = []

        for assessment in high_risk_assessments:
            try:
                plans = self.simulator.generate_plans(assessment, max_plans=3)

                # Save all plans
                for plan in plans:
                    plan.save()

                successful.append({
                    'assessment': assessment,
                    'plans': plans
                })

            except Exception as e:
                failed.append({
                    'assessment': assessment,
                    'error': str(e)
                })

        return {
            'successful': successful,
            'failed': failed,
            'total_attempted': len(high_risk_assessments),
            'success_count': len(successful),
            'failure_count': len(failed)
        }
