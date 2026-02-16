"""
Test script for LLM integration.

Tests both Claude API (if configured) and template fallback.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from apps.planning.models import MitigationPlan
from apps.llm.services.claude_service import ClaudeExplainer, PlanEnhancer

print("=" * 60)
print("JEPCO GRID - LLM INTEGRATION TEST")
print("=" * 60)

# Test 1: Template fallback (always works)
print("\n[Test 1] Testing template fallback...")
try:
    explainer = ClaudeExplainer()
    print(f"Claude API enabled: {explainer.enabled}")

    # Sample plan data
    plan_data = {
        'from_transformer_name': 'T-07',
        'to_transformer_name': 'T-09',
        'transfer_kw': 114.18,
        'switch_name': 'SW-03',
        'risk_before': 0.712,
        'risk_after': 0.154,
        'risk_reduction': 0.558,
        'load_before_pct': 115.37,
        'load_after_pct': 90.0
    }

    fallback = explainer.generate_template_fallback(plan_data)

    print(f"\n[SUCCESS] Template fallback generated:")
    print(f"\nExecutive Summary:")
    print(f"  {fallback['executive_summary']}")
    print(f"\nOperator Steps ({len(fallback['operator_steps'])} steps):")
    for step in fallback['operator_steps'][:3]:
        print(f"  {step}")
    print(f"  ... ({len(fallback['operator_steps']) - 3} more steps)")
    print(f"\nField Checklist ({len(fallback['field_checklist'])} items):")
    for item in fallback['field_checklist'][:3]:
        print(f"  - {item}")
    print(f"  ... ({len(fallback['field_checklist']) - 3} more items)")
    print(f"\nConfidence: {fallback['confidence']}")

except Exception as e:
    print(f"[ERROR] Template fallback failed: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Enhance existing mitigation plan
print("\n" + "=" * 60)
print("[Test 2] Enhancing existing mitigation plan...")
try:
    # Get first mitigation plan
    plan = MitigationPlan.objects.first()

    if not plan:
        print("[ERROR] No mitigation plans found. Run test_planning.py first.")
    else:
        print(f"Plan ID: {plan.id}")
        print(f"Transfer: {plan.plan_json['transfer_kw']:.0f} kW")
        print(f"From: {plan.plan_json['from_transformer_name']}")
        print(f"To: {plan.plan_json['to_transformer_name']}")

        # Check current state
        print(f"\nCurrent LLM confidence: {plan.llm_confidence}")
        print(f"Current operator steps: {len(plan.operator_steps)} steps")

        # Enhance plan
        enhancer = PlanEnhancer(max_retries=1)
        enhanced_plan = enhancer.enhance_plan(plan)

        print(f"\n[SUCCESS] Plan enhanced:")
        print(f"\nExecutive Summary:")
        print(f"  {enhanced_plan.executive_summary[:200]}...")
        print(f"\nOperator Steps ({len(enhanced_plan.operator_steps)} steps):")
        for i, step in enumerate(enhanced_plan.operator_steps[:3], 1):
            print(f"  {step}")
        if len(enhanced_plan.operator_steps) > 3:
            print(f"  ... ({len(enhanced_plan.operator_steps) - 3} more steps)")
        print(f"\nLLM Confidence: {enhanced_plan.llm_confidence}")

        # Save enhanced plan
        enhanced_plan.save()
        print(f"\nPlan saved with LLM enhancements")

except Exception as e:
    print(f"[ERROR] Plan enhancement failed: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Bulk enhancement
print("\n" + "=" * 60)
print("[Test 3] Bulk enhancement of all plans...")
try:
    plans = MitigationPlan.objects.all()[:5]  # Limit to 5 for testing

    if not plans:
        print("[ERROR] No plans to enhance")
    else:
        print(f"Found {len(plans)} plans to enhance")

        enhancer = PlanEnhancer(max_retries=1)
        result = enhancer.bulk_enhance(plans)

        print(f"\n[SUCCESS] Bulk enhancement complete:")
        print(f"  Enhanced: {result['enhanced']}")
        print(f"  Failed: {result['failed']}")
        print(f"  Total: {result['total']}")

        # Save all enhanced plans
        for plan in plans:
            plan.save()

        print(f"\nAll enhanced plans saved")

except Exception as e:
    print(f"[ERROR] Bulk enhancement failed: {e}")
    import traceback
    traceback.print_exc()

# Summary
print("\n" + "=" * 60)
print("[SUMMARY] LLM Integration Test Results")
print("=" * 60)

total_plans = MitigationPlan.objects.count()
enhanced_plans = MitigationPlan.objects.filter(llm_confidence__gt=0).count()

print(f"Total Plans: {total_plans}")
print(f"Enhanced Plans: {enhanced_plans}")

if enhanced_plans > 0:
    print(f"\nSample Enhanced Plan:")
    sample = MitigationPlan.objects.filter(llm_confidence__gt=0).first()
    if sample:
        print(f"  Plan ID: {sample.id}")
        print(f"  Transformer: {sample.assessment.transformer.name}")
        print(f"  LLM Confidence: {sample.llm_confidence}")
        print(f"  Operator Steps: {len(sample.operator_steps)}")
        print(f"  Field Checklist: {len(sample.field_checklist)}")
        print(f"  Rollback Steps: {len(sample.rollback_steps)}")
        print(f"  Assumptions: {len(sample.assumptions)}")

print("\n" + "=" * 60)
print("[COMPLETE] All LLM tests finished")
print("=" * 60)
print("\nNOTE: If ANTHROPIC_API_KEY is not configured, template fallback will be used.")
print("This provides functional (though less detailed) instructions without AI enhancement.")
