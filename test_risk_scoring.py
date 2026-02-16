"""
Test script for risk scoring functionality.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from apps.assets.models import Transformer
from apps.forecasting.models import LoadForecast
from apps.risk.services.risk_scorer import RiskScorer, BulkRiskScorer

print("=" * 60)
print("JEPCO GRID - RISK SCORING TEST")
print("=" * 60)

# Test 1: Single transformer risk assessment
print("\n[Test 1] Generating risk assessment for T-07...")
try:
    t7 = Transformer.objects.get(name='T-07')
    forecast = LoadForecast.objects.filter(transformer=t7).order_by('-forecast_generated_at').first()

    if not forecast:
        print("[ERROR] No forecast found for T-07. Run forecasting first.")
    else:
        scorer = RiskScorer()
        assessment = scorer.score_transformer(t7, forecast)

        print(f"\nTransformer: {assessment.transformer.name}")
        print(f"Risk Score: {assessment.risk_score} ({assessment.risk_level})")
        print(f"Overload: {assessment.overload_pct}%")
        print(f"Confidence: {assessment.confidence}")
        print(f"\nRisk Components:")
        print(f"  Overload: {assessment.risk_components['overload']} (weight: 60%)")
        print(f"  Thermal: {assessment.risk_components['thermal']} (weight: 20%)")
        print(f"  Cascading: {assessment.risk_components['cascading']} (weight: 20%)")
        print(f"\nPrimary Reason: {assessment.reasons_json['primary']}")
        print(f"\nDetailed Reasons:")
        for bullet in assessment.reasons_json['bullets']:
            print(f"  - {bullet}")
        print(f"\nRecommendations:")
        for rec in assessment.reasons_json['recommendations']:
            print(f"  - {rec}")
        print(f"\nRequires Action: {assessment.requires_action}")

        print(f"\n[SUCCESS] Risk assessment saved (ID: {assessment.id})")

except Exception as e:
    print(f"[ERROR] {e}")

# Test 2: Bulk risk scoring
print("\n" + "=" * 60)
print("[Test 2] Generating risk assessments for all transformers...")
try:
    bulk_scorer = BulkRiskScorer()
    result = bulk_scorer.score_all_transformers()

    print(f"\nResults:")
    print(f"  Total attempted: {result['total_attempted']}")
    print(f"  Successful: {result['success_count']}")
    print(f"  Failed: {result['failure_count']}")

    if result['successful']:
        # Group by risk level
        high_risk = [a for a in result['successful'] if a.risk_level == 'HIGH']
        medium_risk = [a for a in result['successful'] if a.risk_level == 'MEDIUM']
        low_risk = [a for a in result['successful'] if a.risk_level == 'LOW']

        print(f"\nRisk Distribution:")
        print(f"  HIGH Risk (>= 0.7): {len(high_risk)} transformers")
        print(f"  MEDIUM Risk (0.3-0.7): {len(medium_risk)} transformers")
        print(f"  LOW Risk (< 0.3): {len(low_risk)} transformers")

        if high_risk:
            print(f"\n[ALERT] High-Risk Transformers:")
            for assessment in sorted(high_risk, key=lambda x: x.risk_score, reverse=True):
                print(f"  {assessment.transformer.name}: Score {assessment.risk_score} - {assessment.reasons_json['primary']}")

        if medium_risk:
            print(f"\n[WARNING] Medium-Risk Transformers:")
            for assessment in medium_risk:
                print(f"  {assessment.transformer.name}: Score {assessment.risk_score}")

    if result['failed']:
        print(f"\n[ERRORS] Failed assessments:")
        for failure in result['failed']:
            print(f"  {failure['transformer'].name}: {failure['error']}")

    print(f"\n[SUCCESS] Bulk risk scoring complete")

except Exception as e:
    print(f"[ERROR] Bulk risk scoring failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("[COMPLETE] All risk scoring tests finished")
print("=" * 60)
