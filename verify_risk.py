"""
Verification script for risk assessment data.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from apps.risk.models import RiskAssessment

print("=" * 60)
print("RISK ASSESSMENT DATA VERIFICATION")
print("=" * 60)

# Get all assessments
assessments = RiskAssessment.objects.all().select_related('transformer', 'forecast')

print(f"\nTotal Assessments: {assessments.count()}")

# Risk level breakdown
high_risk = assessments.filter(risk_level='HIGH')
medium_risk = assessments.filter(risk_level='MEDIUM')
low_risk = assessments.filter(risk_level='LOW')

print(f"\n[+] Risk Level Distribution:")
print(f"   HIGH Risk (>= 0.7): {high_risk.count()} transformers")
print(f"   MEDIUM Risk (0.3-0.7): {medium_risk.count()} transformers")
print(f"   LOW Risk (< 0.3): {low_risk.count()} transformers")

# Action required
action_required = assessments.filter(risk_score__gte=0.7)
print(f"\n[+] Transformers Requiring Action: {action_required.count()}")

for assessment in action_required:
    print(f"\n   Transformer: {assessment.transformer.name}")
    print(f"   Risk Score: {assessment.risk_score} ({assessment.risk_level})")
    print(f"   Overload: {assessment.overload_pct}%")
    print(f"   Components: Overload={assessment.risk_components['overload']}, Thermal={assessment.risk_components['thermal']}, Cascading={assessment.risk_components['cascading']}")
    print(f"   Primary Reason: {assessment.reasons_json['primary']}")
    print(f"   Time Window: {assessment.time_window_start.strftime('%Y-%m-%d %H:%M')} to {assessment.time_window_end.strftime('%Y-%m-%d %H:%M')}")

# Sample detailed assessment
print(f"\n[+] Sample Detailed Assessment (T-04):")
t4_assessment = assessments.filter(transformer__name='T-04').first()
if t4_assessment:
    print(f"   Transformer: {t4_assessment.transformer.name}")
    print(f"   Rated capacity: {t4_assessment.transformer.rated_kw} kW")
    print(f"   Risk Score: {t4_assessment.risk_score} ({t4_assessment.risk_level})")
    print(f"   Overload: {t4_assessment.overload_pct}%")
    print(f"   Confidence: {t4_assessment.confidence}")
    print(f"\n   Risk Components Breakdown:")
    print(f"      Overload Component: {t4_assessment.risk_components['overload']}")
    print(f"      Thermal Component: {t4_assessment.risk_components['thermal']}")
    print(f"      Cascading Component: {t4_assessment.risk_components['cascading']}")
    print(f"\n   Weighted Contributions:")
    print(f"      Overload (60%): {float(t4_assessment.risk_components['overload']) * 0.6:.3f}")
    print(f"      Thermal (20%): {float(t4_assessment.risk_components['thermal']) * 0.2:.3f}")
    print(f"      Cascading (20%): {float(t4_assessment.risk_components['cascading']) * 0.2:.3f}")
    print(f"      Total: {t4_assessment.risk_score}")
    print(f"\n   Reasons:")
    for bullet in t4_assessment.reasons_json.get('bullets', []):
        print(f"      - {bullet}")
    print(f"\n   Recommendations:")
    for rec in t4_assessment.reasons_json.get('recommendations', []):
        print(f"      - {rec}")

print("\n" + "=" * 60)
print("[SUCCESS] Risk assessment verification complete!")
print("=" * 60)
