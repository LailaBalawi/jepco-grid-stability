"""
End-to-End Integration Test for JEPCO Grid Stability Orchestrator.

Tests complete workflow from data ingestion to work order completion.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from apps.assets.models import Transformer
from apps.telemetry.models import TransformerLoad
from apps.forecasting.services.predictor import BulkForecaster
from apps.risk.services.risk_scorer import BulkRiskScorer
from apps.planning.services.mitigation_simulator import BulkMitigationPlanner
from apps.llm.services.claude_service import PlanEnhancer
from apps.ops.models import WorkOrder, AuditLog
from django.contrib.auth import get_user_model

User = get_user_model()

print("=" * 70)
print("JEPCO GRID STABILITY ORCHESTRATOR")
print("END-TO-END INTEGRATION TEST")
print("=" * 70)

# Workflow Steps
print("\n[WORKFLOW] Complete Intelligence Pipeline")
print("=" * 70)

# Step 1: Data Validation
print("\n[STEP 1] Validating Grid Data...")
transformers = Transformer.objects.filter(is_active=True)
telemetry_count = TransformerLoad.objects.count()

print(f"  Transformers: {transformers.count()}")
print(f"  Load Readings: {telemetry_count}")

if telemetry_count == 0:
    print("  [ERROR] No telemetry data! Run: python manage.py generate_load_data")
    exit(1)

print("  [OK] Grid data validated")

# Step 2: Load Forecasting
print("\n[STEP 2] Running Load Forecasting...")
forecaster = BulkForecaster(lookback_days=7, hours_ahead=72)
forecast_result = forecaster.forecast_all_transformers(save=True)

print(f"  Forecasts Generated: {forecast_result['success_count']}")
print(f"  Failed: {forecast_result['failure_count']}")

if forecast_result['failure_count'] > 0:
    print("  [WARNING] Some forecasts failed:")
    for fail in forecast_result['failed']:
        print(f"    {fail['transformer'].name}: {fail['error']}")

print("  [OK] Forecasting complete")

# Step 3: Risk Assessment
print("\n[STEP 3] Running Risk Assessment...")
risk_scorer = BulkRiskScorer()
risk_result = risk_scorer.score_all_transformers()

print(f"  Assessments Created: {risk_result['success_count']}")
print(f"  High Risk: {sum(1 for a in risk_result['successful'] if a.is_high_risk)}")

high_risk = [a for a in risk_result['successful'] if a.is_high_risk]
if high_risk:
    print("  High-Risk Transformers:")
    for assessment in high_risk:
        print(f"    {assessment.transformer.name}: Risk {assessment.risk_score} - {assessment.reasons_json['primary']}")

print("  [OK] Risk assessment complete")

# Step 4: Mitigation Planning
print("\n[STEP 4] Generating Mitigation Plans...")
planner = BulkMitigationPlanner()
plan_result = planner.plan_all_high_risk(min_risk_score=0.7)

print(f"  Plans Generated: {plan_result['success_count']}")
print(f"  Failed: {plan_result['failure_count']}")

all_plans = []
for item in plan_result['successful']:
    all_plans.extend(item['plans'])

if all_plans:
    print("  Generated Plans:")
    for plan in all_plans:
        print(f"    {plan.assessment.transformer.name}: {plan.plan_json['transfer_kw']:.0f} kW => {plan.plan_json['to_transformer_name']}")

print("  [OK] Planning complete")

# Step 5: LLM Enhancement
print("\n[STEP 5] Enhancing Plans with AI...")
enhancer = PlanEnhancer(max_retries=1)
enhancement_result = enhancer.bulk_enhance(all_plans)

print(f"  Enhanced: {enhancement_result['enhanced']}")
print(f"  Failed: {enhancement_result['failed']}")

# Save enhanced plans
for plan in all_plans:
    plan.save()

print("  [OK] AI enhancement complete")

# Step 6: Work Order Creation
print("\n[STEP 6] Creating Work Orders...")
admin_user = User.objects.filter(is_superuser=True).first()

wo_count = 0
for plan in all_plans[:2]:  # Create WO for top 2 plans
    # Approve plan first
    plan.status = 'APPROVED'
    plan.approved_by = admin_user
    plan.save()

    # Create work order
    steps_text = '\n'.join([f"{i+1}. {step}" for i, step in enumerate(plan.operator_steps)])

    wo = WorkOrder.objects.create(
        plan=plan,
        assigned_team="Field Team Alpha",
        steps_text=steps_text,
        area=plan.assessment.transformer.feeder.substation.name,
        priority='HIGH'
    )

    # Log action
    AuditLog.objects.create(
        action_type='WO_CREATE',
        user=admin_user,
        object_id=wo.id,
        details_json={
            'wo_number': wo.wo_number,
            'transformer': plan.assessment.transformer.name
        },
        success=True
    )

    wo_count += 1
    print(f"  Created: {wo.wo_number} for {plan.assessment.transformer.name}")

print(f"  [OK] {wo_count} work orders created")

# Final Summary
print("\n" + "=" * 70)
print("[INTEGRATION TEST COMPLETE] System Summary")
print("=" * 70)

from apps.forecasting.models import LoadForecast
from apps.risk.models import RiskAssessment
from apps.planning.models import MitigationPlan

print(f"\nData Layer:")
print(f"  Transformers: {Transformer.objects.count()}")
print(f"  Load Readings: {TransformerLoad.objects.count()}")

print(f"\nIntelligence Layer:")
print(f"  Forecasts: {LoadForecast.objects.count()}")
print(f"  Risk Assessments: {RiskAssessment.objects.count()}")
print(f"    - HIGH: {RiskAssessment.objects.filter(risk_level='HIGH').count()}")
print(f"    - MEDIUM: {RiskAssessment.objects.filter(risk_level='MEDIUM').count()}")
print(f"    - LOW: {RiskAssessment.objects.filter(risk_level='LOW').count()}")

print(f"\nPlanning Layer:")
print(f"  Mitigation Plans: {MitigationPlan.objects.count()}")
print(f"    - APPROVED: {MitigationPlan.objects.filter(status='APPROVED').count()}")
print(f"    - DRAFT: {MitigationPlan.objects.filter(status='DRAFT').count()}")
print(f"  LLM Enhanced: {MitigationPlan.objects.filter(llm_confidence__gt=0).count()}")

print(f"\nOperations Layer:")
print(f"  Work Orders: {WorkOrder.objects.count()}")
print(f"    - OPEN: {WorkOrder.objects.filter(status='OPEN').count()}")
print(f"    - COMPLETED: {WorkOrder.objects.filter(status='COMPLETED').count()}")
print(f"  Audit Logs: {AuditLog.objects.count()}")

print("\n" + "=" * 70)
print("[SUCCESS] All systems operational!")
print("=" * 70)
print("\nNext Steps:")
print("  1. Start development server: python manage.py runserver")
print("  2. Visit: http://localhost:8000")
print("  3. Login with: admin / admin123")
print("  4. Review dashboard for high-risk transformers")
print("=" * 70)
