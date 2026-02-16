"""
Claude API Integration Service for JEPCO Grid.

Generates human-readable, safety-focused action plans using Claude API.

CRITICAL SAFETY RULES:
- Only use data provided in the input JSON
- Do NOT invent switch states or transformer capacities
- Include standard electrical safety reminders (PPE, lockout/tagout)
- No dangerous instructions beyond standard utility procedures
- If data is missing, say "insufficient data" in assumptions
"""

import json
import logging
from decimal import Decimal
from django.conf import settings

logger = logging.getLogger(__name__)


class ClaudeExplainer:
    """
    Generate operator-ready action plans using Claude API.

    This service takes structured plan data and generates:
    - Executive summary (3-5 sentences, plain language)
    - Operator steps (control room instructions)
    - Field checklist (safety procedures)
    - Rollback steps (emergency reversion)
    - Assumptions (uncertainties and confidence)
    """

    def __init__(self):
        """Initialize Claude client."""
        self.api_key = getattr(settings, 'ANTHROPIC_API_KEY', None)
        self.model = getattr(settings, 'ANTHROPIC_MODEL', 'claude-sonnet-4-5-20250929')
        self.max_tokens = getattr(settings, 'ANTHROPIC_MAX_TOKENS', 2048)
        self.temperature = 0.3  # Low temperature for consistent, safety-focused output

        if self.api_key:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
                self.enabled = True
                logger.info("Claude API client initialized successfully")
            except ImportError:
                logger.warning("anthropic package not installed, LLM features disabled")
                self.enabled = False
            except Exception as e:
                logger.error(f"Failed to initialize Claude client: {e}")
                self.enabled = False
        else:
            logger.warning("ANTHROPIC_API_KEY not configured, LLM features disabled")
            self.enabled = False

    def generate_action_plan(self, plan_data):
        """
        Generate enhanced action plan with LLM.

        Args:
            plan_data (dict): Structured plan from MitigationSimulator
                {
                    'from_transformer_name': 'T-07',
                    'to_transformer_name': 'T-09',
                    'transfer_kw': 114.18,
                    'switch_name': 'SW-03',
                    'risk_before': 0.712,
                    'risk_after': 0.154,
                    'load_before_pct': 115.37,
                    'load_after_pct': 90.0,
                    ...
                }

        Returns:
            dict: {
                'executive_summary': str,
                'operator_steps': list[str],
                'field_checklist': list[str],
                'rollback_steps': list[str],
                'assumptions': list[str],
                'confidence': float
            }

        Raises:
            Exception: If LLM call fails (caller should use template fallback)
        """
        if not self.enabled:
            raise Exception("Claude API not available")

        # Build prompt
        prompt = self._build_prompt(plan_data)

        try:
            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=self._get_system_prompt(),
                messages=[{"role": "user", "content": prompt}]
            )

            # Extract text from response
            output_text = response.content[0].text

            # Parse JSON output
            output = json.loads(output_text)

            # Validate schema
            validated = self._validate_schema(output)

            logger.info(f"Successfully generated action plan for {plan_data.get('from_transformer_name')}")
            return validated

        except json.JSONDecodeError as e:
            logger.error(f"LLM returned invalid JSON: {e}")
            raise Exception(f"LLM JSON parsing failed: {e}")

        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            raise Exception(f"LLM API error: {e}")

    def _get_system_prompt(self):
        """
        Get system prompt with safety guidelines.

        Returns:
            str: System prompt for Claude
        """
        return """You are an expert electrical grid operations advisor for JEPCO (Jordan Electric Power Company).

CRITICAL RULES:
- Only use data provided in the input JSON
- Do NOT invent switch states or transformer capacities
- Output MUST be valid JSON matching the exact schema provided
- Include standard electrical safety reminders (PPE, lockout/tagout, voltage verification)
- No dangerous instructions beyond standard utility procedures
- If data is missing, say "insufficient data" in assumptions
- Use clear, professional language suitable for control room operators

Output schema (MUST match exactly):
{
  "executive_summary": "3-5 sentence plain language summary explaining what, why, and expected outcome",
  "operator_steps": ["Step 1: ...", "Step 2: ...", ...],
  "field_checklist": ["PPE verification", "Lockout/tagout", "Voltage verification", ...],
  "rollback_steps": ["If voltage >X, revert switch Y", "If customer complaints, ...", ...],
  "assumptions": ["Forecast error ±6%", "Weather conditions stable", ...],
  "confidence": 0.82
}

Confidence scoring:
- 0.90-1.0: Complete data, straightforward transfer, minimal risk
- 0.75-0.89: Good data, standard procedure, moderate complexity
- 0.60-0.74: Some uncertainties, requires careful monitoring
- Below 0.60: Insufficient data or high-risk scenario

Safety-first mindset: When in doubt, include additional verification steps."""

    def _build_prompt(self, plan_data):
        """
        Build user prompt from plan data.

        Args:
            plan_data (dict): Plan data from simulator

        Returns:
            str: Formatted prompt
        """
        prompt = f"""Generate a detailed action plan for this load transfer operation:

TRANSFORMER INFORMATION:
- Source: {plan_data.get('from_transformer_name', 'Unknown')}
- Destination: {plan_data.get('to_transformer_name', 'Unknown')}
- Transfer amount: {plan_data.get('transfer_kw', 0):.0f} kW
- Via switch: {plan_data.get('switch_name', 'Unknown')}

CURRENT STATE:
- Source load: {plan_data.get('load_before_pct', 0):.1f}% of rated capacity
- Risk score: {plan_data.get('risk_before', 0):.3f} (HIGH)

EXPECTED OUTCOME:
- Source load after transfer: {plan_data.get('load_after_pct', 0):.1f}%
- Risk score after transfer: {plan_data.get('risk_after', 0):.3f} (LOW)
- Risk reduction: {plan_data.get('risk_reduction', 0):.3f}

OBJECTIVE:
Prevent transformer overload by safely transferring {plan_data.get('transfer_kw', 0):.0f} kW to a neighbor transformer with available capacity.

Generate a complete action plan with:
1. Executive summary (why this transfer is necessary, what it achieves)
2. Operator steps (5-8 steps for control room, including pre-checks, switching sequence, monitoring)
3. Field checklist (safety procedures: PPE, lockout/tagout, voltage verification, etc.)
4. Rollback steps (what to do if voltage deviates, customer complaints, or unexpected behavior)
5. Assumptions (forecast accuracy, weather stability, no concurrent outages, etc.)
6. Confidence score (0.0-1.0 based on data completeness and operation complexity)

Return ONLY valid JSON matching the schema. No additional text."""

        return prompt

    def _validate_schema(self, output):
        """
        Validate LLM output matches required schema.

        Args:
            output (dict): Parsed JSON from LLM

        Returns:
            dict: Validated output

        Raises:
            ValueError: If schema validation fails
        """
        required_keys = [
            'executive_summary',
            'operator_steps',
            'field_checklist',
            'rollback_steps',
            'assumptions',
            'confidence'
        ]

        # Check all required keys present
        for key in required_keys:
            if key not in output:
                raise ValueError(f"Missing required key: {key}")

        # Validate types
        if not isinstance(output['executive_summary'], str):
            raise ValueError("executive_summary must be string")

        if not isinstance(output['operator_steps'], list):
            raise ValueError("operator_steps must be array")

        if not isinstance(output['field_checklist'], list):
            raise ValueError("field_checklist must be array")

        if not isinstance(output['rollback_steps'], list):
            raise ValueError("rollback_steps must be array")

        if not isinstance(output['assumptions'], list):
            raise ValueError("assumptions must be array")

        # Validate confidence is numeric and in range
        try:
            confidence = float(output['confidence'])
            if not (0.0 <= confidence <= 1.0):
                raise ValueError("confidence must be 0.0-1.0")
            output['confidence'] = confidence
        except (TypeError, ValueError) as e:
            raise ValueError(f"confidence must be numeric 0.0-1.0: {e}")

        # Validate lists are not empty
        if len(output['operator_steps']) == 0:
            raise ValueError("operator_steps cannot be empty")

        if len(output['field_checklist']) == 0:
            raise ValueError("field_checklist cannot be empty")

        if len(output['rollback_steps']) == 0:
            raise ValueError("rollback_steps cannot be empty")

        # Validate summary is not too short
        if len(output['executive_summary']) < 50:
            raise ValueError("executive_summary too short (min 50 chars)")

        return output

    def generate_template_fallback(self, plan_data):
        """
        Generate template-based plan when LLM is unavailable.

        This provides basic but functional instructions without AI enhancement.

        Args:
            plan_data (dict): Plan data from simulator

        Returns:
            dict: Template-based action plan
        """
        from_name = plan_data.get('from_transformer_name', 'source')
        to_name = plan_data.get('to_transformer_name', 'destination')
        transfer_kw = plan_data.get('transfer_kw', 0)
        switch_name = plan_data.get('switch_name', 'tie switch')
        load_before = plan_data.get('load_before_pct', 0)
        load_after = plan_data.get('load_after_pct', 0)
        risk_reduction = plan_data.get('risk_reduction', 0)

        return {
            'executive_summary': (
                f"Transformer {from_name} is predicted to reach {load_before:.1f}% load, "
                f"exceeding safe operating limits. Transferring {transfer_kw:.0f} kW to {to_name} "
                f"via {switch_name} will reduce load to {load_after:.1f}% and decrease risk by {risk_reduction:.3f}. "
                f"This is a standard load balancing operation following JEPCO procedures."
            ),
            'operator_steps': [
                f"1. Verify {switch_name} is available and not under maintenance",
                f"2. Confirm {to_name} has sufficient capacity (check current load < 85%)",
                "3. Notify field crew and obtain confirmation of readiness",
                f"4. Close {switch_name} to enable load transfer",
                f"5. Monitor voltage and load on both {from_name} and {to_name} for 10 minutes",
                f"6. Verify {from_name} load drops to expected level",
                "7. Confirm no customer complaints or voltage issues",
                "8. Document operation in system logs"
            ],
            'field_checklist': [
                "Personal Protective Equipment (PPE) verified and worn",
                "Lockout/tagout procedures followed per JEPCO standards",
                "Voltage verification performed before switch operation",
                "Communication equipment functional and tested",
                "Emergency contacts and rollback plan reviewed",
                "Weather conditions checked (avoid operations during storms)",
                "Backup crew notified and on standby"
            ],
            'rollback_steps': [
                f"1. If voltage deviation exceeds 1.05 per-unit, immediately reopen {switch_name}",
                "2. If customer complaints received within 5 minutes, revert operation",
                f"3. If {to_name} load exceeds 90%, partial rollback may be required",
                "4. Notify control room supervisor of any abnormal conditions",
                "5. Document all observations and actions taken",
                "6. Await further instructions before re-attempting transfer"
            ],
            'assumptions': [
                "Forecast accuracy ±6% based on historical performance",
                "Weather conditions remain stable during operation",
                "No concurrent outages or maintenance in the area",
                f"{to_name} transformer is operating normally",
                "Communication systems remain functional",
                "Standard JEPCO safety procedures are followed"
            ],
            'confidence': 0.75  # Template fallback has moderate confidence
        }


class PlanEnhancer:
    """
    Enhance mitigation plans with LLM-generated instructions.

    Wraps ClaudeExplainer with retry logic and fallback mechanisms.
    """

    def __init__(self, max_retries=2):
        """
        Initialize plan enhancer.

        Args:
            max_retries (int): Number of retry attempts for LLM calls
        """
        self.explainer = ClaudeExplainer()
        self.max_retries = max_retries

    def enhance_plan(self, mitigation_plan):
        """
        Enhance a MitigationPlan with LLM-generated content.

        Args:
            mitigation_plan (MitigationPlan): Plan instance to enhance

        Returns:
            MitigationPlan: Enhanced plan (modified in-place)
        """
        plan_data = mitigation_plan.plan_json

        # Try LLM first (with retries)
        for attempt in range(self.max_retries + 1):
            try:
                enhanced = self.explainer.generate_action_plan(plan_data)

                # Update plan with LLM output
                mitigation_plan.executive_summary = enhanced['executive_summary']
                mitigation_plan.operator_steps = enhanced['operator_steps']
                mitigation_plan.field_checklist = enhanced['field_checklist']
                mitigation_plan.rollback_steps = enhanced['rollback_steps']
                mitigation_plan.assumptions = enhanced['assumptions']
                mitigation_plan.llm_confidence = Decimal(str(enhanced['confidence']))

                logger.info(f"Plan {mitigation_plan.id} enhanced with LLM (attempt {attempt + 1})")
                return mitigation_plan

            except Exception as e:
                logger.warning(f"LLM enhancement attempt {attempt + 1} failed: {e}")

                if attempt == self.max_retries:
                    # All retries exhausted, use template fallback
                    logger.info(f"Using template fallback for plan {mitigation_plan.id}")
                    fallback = self.explainer.generate_template_fallback(plan_data)

                    mitigation_plan.executive_summary = fallback['executive_summary']
                    mitigation_plan.operator_steps = fallback['operator_steps']
                    mitigation_plan.field_checklist = fallback['field_checklist']
                    mitigation_plan.rollback_steps = fallback['rollback_steps']
                    mitigation_plan.assumptions = fallback['assumptions']
                    mitigation_plan.llm_confidence = Decimal(str(fallback['confidence']))

                    return mitigation_plan

        return mitigation_plan

    def bulk_enhance(self, mitigation_plans):
        """
        Enhance multiple plans.

        Args:
            mitigation_plans (list): List of MitigationPlan instances

        Returns:
            dict: {
                'enhanced': count,
                'failed': count,
                'total': count
            }
        """
        enhanced_count = 0
        failed_count = 0

        for plan in mitigation_plans:
            try:
                self.enhance_plan(plan)
                enhanced_count += 1
            except Exception as e:
                logger.error(f"Failed to enhance plan {plan.id}: {e}")
                failed_count += 1

        return {
            'enhanced': enhanced_count,
            'failed': failed_count,
            'total': len(mitigation_plans)
        }
