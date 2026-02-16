"""
Test script for Ops app (Work Orders & Audit).
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from apps.planning.models import MitigationPlan
from apps.ops.models import WorkOrder, AuditLog
from django.contrib.auth import get_user_model

User = get_user_model()

print("=" * 60)
print("JEPCO GRID - OPS APP TEST")
print("=" * 60)

# Test 1: Create work order from approved plan
print("\n[Test 1] Creating work order from plan...")
try:
    # Get first enhanced plan
    plan = MitigationPlan.objects.filter(llm_confidence__gt=0).first()

    if not plan:
        print("[ERROR] No plans found. Run previous tests first.")
    else:
        # Approve the plan first
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            print("[WARNING] No admin user, creating one...")
            admin_user = User.objects.create_superuser('admin', 'admin@jepco.jo', 'admin123')

        plan.status = 'APPROVED'
        plan.approved_by = admin_user
        plan.save()

        print(f"Plan {plan.id} approved: {plan.assessment.transformer.name}")

        # Create work order
        steps_text = '\n'.join([f"{i+1}. {step}" for i, step in enumerate(plan.operator_steps)])

        wo = WorkOrder.objects.create(
            plan=plan,
            assigned_team="Field Team Alpha",
            steps_text=steps_text,
            area=plan.assessment.transformer.feeder.substation.name,
            priority='HIGH'
        )

        print(f"\n[SUCCESS] Work Order Created:")
        print(f"  WO Number: {wo.wo_number}")
        print(f"  Transformer: {plan.assessment.transformer.name}")
        print(f"  Area: {wo.area}")
        print(f"  Team: {wo.assigned_team}")
        print(f"  Priority: {wo.priority}")
        print(f"  Status: {wo.status}")
        print(f"  Steps: {len(plan.operator_steps)} operator steps")

        # Create audit log
        AuditLog.objects.create(
            action_type='WO_CREATE',
            user=admin_user,
            object_id=wo.id,
            details_json={
                'wo_number': wo.wo_number,
                'plan_id': plan.id,
                'transformer': plan.assessment.transformer.name
            },
            success=True
        )
        print(f"  Audit log created")

except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()

# Test 2: Work order lifecycle
print("\n" + "=" * 60)
print("[Test 2] Testing work order lifecycle...")
try:
    wo = WorkOrder.objects.first()

    if not wo:
        print("[ERROR] No work orders found")
    else:
        print(f"Work Order: {wo.wo_number}")
        print(f"Initial Status: {wo.status}")

        # Start work order
        wo.status = 'IN_PROGRESS'
        wo.save()
        print(f"Status after start: {wo.status}")

        # Complete work order
        wo.status = 'COMPLETED'
        wo.outcome_notes = "Load transfer completed successfully. T-07 load reduced from 115% to 91%. No customer impacts observed."
        wo.save()
        print(f"Status after completion: {wo.status}")
        print(f"Outcome: {wo.outcome_notes[:80]}...")

        print(f"\n[SUCCESS] Work order lifecycle test complete")

except Exception as e:
    print(f"[ERROR] {e}")

# Test 3: Audit log query
print("\n" + "=" * 60)
print("[Test 3] Querying audit logs...")
try:
    logs = AuditLog.objects.all()[:10]

    print(f"Total audit logs: {AuditLog.objects.count()}")
    print(f"\nRecent logs:")
    for log in logs:
        user_str = log.user.username if log.user else 'System'
        print(f"  [{log.timestamp.strftime('%H:%M:%S')}] {user_str} - {log.action_type} - {'Success' if log.success else 'Failed'}")

    print(f"\n[SUCCESS] Audit log query complete")

except Exception as e:
    print(f"[ERROR] {e}")

# Summary
print("\n" + "=" * 60)
print("[SUMMARY] Ops App Statistics")
print("=" * 60)

total_wo = WorkOrder.objects.count()
open_wo = WorkOrder.objects.filter(status='OPEN').count()
in_progress_wo = WorkOrder.objects.filter(status='IN_PROGRESS').count()
completed_wo = WorkOrder.objects.filter(status='COMPLETED').count()

print(f"Work Orders:")
print(f"  Total: {total_wo}")
print(f"  Open: {open_wo}")
print(f"  In Progress: {in_progress_wo}")
print(f"  Completed: {completed_wo}")

total_logs = AuditLog.objects.count()
wo_logs = AuditLog.objects.filter(action_type__startswith='WO_').count()

print(f"\nAudit Logs:")
print(f"  Total: {total_logs}")
print(f"  Work Order Related: {wo_logs}")

if total_wo > 0:
    sample_wo = WorkOrder.objects.first()
    print(f"\nSample Work Order:")
    print(f"  Number: {sample_wo.wo_number}")
    print(f"  Area: {sample_wo.area}")
    print(f"  Team: {sample_wo.assigned_team}")
    print(f"  Status: {sample_wo.status}")
    print(f"  Priority: {sample_wo.priority}")
    print(f"  Overdue: {sample_wo.is_overdue}")

print("\n" + "=" * 60)
print("[COMPLETE] All ops tests finished")
print("=" * 60)
