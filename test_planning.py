"""
Test script for mitigation planning functionality.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from apps.risk.models import RiskAssessment
from apps.planning.services.mitigation_simulator import MitigationSimulator, BulkMitigationPlanner

print("=" * 60)
print("JEPCO GRID - MITIGATION PLANNING TEST")
print("=" * 60)

# Test 1: Generate plans for T-07 (high risk transformer)
print("\n[Test 1] Generating mitigation plans for T-07...")
try:
    # Get the high-risk assessment for T-07
    t7_assessment = RiskAssessment.objects.filter(
        transformer__name='T-07',
        risk_level='HIGH'
    ).select_related('transformer', 'forecast').first()

    if not t7_assessment:
        print("[ERROR] No high-risk assessment found for T-07. Run risk scoring first.")
    else:
        print(f"Assessment: {t7_assessment.transformer.name}")
        print(f"Risk Score: {t7_assessment.risk_score} ({t7_assessment.risk_level})")
        print(f"Overload: {t7_assessment.overload_pct}%")

        # Generate mitigation plans
        simulator = MitigationSimulator()
        plans = simulator.generate_plans(t7_assessment, max_plans=3)

        print(f"\n[SUCCESS] Generated {len(plans)} mitigation plans:")

        for i, plan in enumerate(plans, 1):
            print(f"\n--- Plan {i} ---")
            print(f"Transfer: {plan.plan_json['transfer_kw']} kW")
            print(f"From: {plan.plan_json['from_transformer_name']}")
            print(f"To: {plan.plan_json['to_transformer_name']}")
            print(f"Via Switch: {plan.plan_json['switch_name']}")
            print(f"Risk Before: {plan.plan_json['risk_before']}")
            print(f"Risk After: {plan.plan_json['risk_after']}")
            print(f"Risk Reduction: {plan.plan_json['risk_reduction']}")
            print(f"Load Before: {plan.plan_json['load_before_pct']}%")
            print(f"Load After: {plan.plan_json['load_after_pct']}%")
            print(f"\nOperator Steps:")
            for step in plan.operator_steps:
                print(f"  {step}")

            # Save the plan
            plan.save()
            print(f"\nPlan saved (ID: {plan.id})")

except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()

# Test 2: Bulk planning for all high-risk transformers
print("\n" + "=" * 60)
print("[Test 2] Generating plans for all high-risk transformers...")
try:
    bulk_planner = BulkMitigationPlanner()
    result = bulk_planner.plan_all_high_risk(min_risk_score=0.7)

    print(f"\nResults:")
    print(f"  Total attempted: {result['total_attempted']}")
    print(f"  Successful: {result['success_count']}")
    print(f"  Failed: {result['failure_count']}")

    if result['successful']:
        print(f"\nSuccessful Plans:")
        for item in result['successful']:
            assessment = item['assessment']
            plans = item['plans']
            print(f"\n  Transformer: {assessment.transformer.name}")
            print(f"  Risk Score: {assessment.risk_score}")
            print(f"  Plans Generated: {len(plans)}")

            for i, plan in enumerate(plans, 1):
                risk_reduction = plan.plan_json['risk_reduction']
                transfer_kw = plan.plan_json['transfer_kw']
                to_name = plan.plan_json['to_transformer_name']
                print(f"    Plan {i}: Transfer {transfer_kw:.0f} kW to {to_name} (Risk reduction: {risk_reduction:.3f})")

    if result['failed']:
        print(f"\n[ERRORS] Failed plans:")
        for failure in result['failed']:
            print(f"  {failure['assessment'].transformer.name}: {failure['error']}")

    print(f"\n[SUCCESS] Bulk planning complete")

except Exception as e:
    print(f"[ERROR] Bulk planning failed: {e}")
    import traceback
    traceback.print_exc()

# Summary
print("\n" + "=" * 60)
print("[SUMMARY] Mitigation Planning Statistics")
print("=" * 60)

from apps.planning.models import MitigationPlan

total_plans = MitigationPlan.objects.count()
draft_plans = MitigationPlan.objects.filter(status='DRAFT').count()

print(f"Total Plans Created: {total_plans}")
print(f"Draft Plans: {draft_plans}")

if total_plans > 0:
    print(f"\nTop 3 Plans by Risk Reduction:")
    top_plans = MitigationPlan.objects.all().order_by('-plan_json__risk_reduction')[:3]
    for plan in top_plans:
        trans = plan.assessment.transformer.name
        reduction = plan.plan_json['risk_reduction']
        transfer = plan.plan_json['transfer_kw']
        to = plan.plan_json['to_transformer_name']
        print(f"  {trans}: Transfer {transfer:.0f} kW to {to} (Reduction: {reduction:.3f})")

print("\n" + "=" * 60)
print("[COMPLETE] All planning tests finished")
print("=" * 60)
