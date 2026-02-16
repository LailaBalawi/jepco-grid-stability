"""
API views for Ops app.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import WorkOrder, AuditLog
from .serializers import (
    WorkOrderSerializer,
    WorkOrderListSerializer,
    AuditLogSerializer
)
from apps.planning.models import MitigationPlan


class WorkOrderViewSet(viewsets.ModelViewSet):
    """
    API endpoints for work orders.

    Endpoints:
        GET /api/ops/workorders/ - List all work orders
        GET /api/ops/workorders/{id}/ - Retrieve specific work order
        POST /api/ops/workorders/ - Create work order from plan
        PATCH /api/ops/workorders/{id}/ - Update work order
        POST /api/ops/workorders/{id}/start/ - Mark as started
        POST /api/ops/workorders/{id}/complete/ - Mark as completed
    """

    queryset = WorkOrder.objects.all().select_related(
        'plan',
        'plan__assessment',
        'plan__assessment__transformer'
    )

    filterset_fields = ['status', 'assigned_team', 'priority']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Use lightweight serializer for list views."""
        if self.action == 'list':
            return WorkOrderListSerializer
        return WorkOrderSerializer

    def create(self, request, *args, **kwargs):
        """
        Create work order from approved mitigation plan.

        POST /api/ops/workorders/
        Body: {
            "plan_id": 1,
            "assigned_team": "Field Team Alpha",
            "priority": "HIGH"  # optional
        }
        """
        plan_id = request.data.get('plan_id')
        assigned_team = request.data.get('assigned_team')
        priority = request.data.get('priority', 'MEDIUM')

        if not plan_id or not assigned_team:
            return Response(
                {'error': 'plan_id and assigned_team are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            plan = get_object_or_404(MitigationPlan, pk=plan_id)

            if plan.status != 'APPROVED':
                return Response(
                    {'error': 'Only approved plans can become work orders'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create work order
            steps_text = '\n'.join([f"{i+1}. {step}" for i, step in enumerate(plan.operator_steps)])

            work_order = WorkOrder.objects.create(
                plan=plan,
                assigned_team=assigned_team,
                steps_text=steps_text,
                area=plan.assessment.transformer.feeder.substation.name,
                priority=priority
            )

            # Log action
            AuditLog.objects.create(
                action_type='WO_CREATE',
                user=request.user if request.user.is_authenticated else None,
                content_type=None,
                object_id=work_order.id,
                details_json={
                    'wo_number': work_order.wo_number,
                    'plan_id': plan.id,
                    'transformer': plan.assessment.transformer.name
                },
                success=True
            )

            serializer = WorkOrderSerializer(work_order)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'error': f'Work order creation failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """
        Mark work order as started.

        POST /api/ops/workorders/{id}/start/
        """
        work_order = self.get_object()

        if work_order.status != 'OPEN':
            return Response(
                {'error': 'Only open work orders can be started'},
                status=status.HTTP_400_BAD_REQUEST
            )

        work_order.status = 'IN_PROGRESS'
        work_order.started_at = timezone.now()
        work_order.save()

        # Log action
        AuditLog.objects.create(
            action_type='WO_START',
            user=request.user if request.user.is_authenticated else None,
            object_id=work_order.id,
            details_json={'wo_number': work_order.wo_number},
            success=True
        )

        serializer = WorkOrderSerializer(work_order)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """
        Mark work order as completed.

        POST /api/ops/workorders/{id}/complete/
        Body: {
            "outcome_notes": "..."  # required
        }
        """
        work_order = self.get_object()

        if work_order.status not in ['OPEN', 'IN_PROGRESS']:
            return Response(
                {'error': 'Work order already completed or cancelled'},
                status=status.HTTP_400_BAD_REQUEST
            )

        outcome_notes = request.data.get('outcome_notes', '')
        if not outcome_notes:
            return Response(
                {'error': 'outcome_notes are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        work_order.status = 'COMPLETED'
        work_order.completed_at = timezone.now()
        work_order.outcome_notes = outcome_notes
        work_order.save()

        # Mark plan as executed
        work_order.plan.status = 'EXECUTED'
        work_order.plan.executed_at = timezone.now()
        work_order.plan.executed_by = request.user if request.user.is_authenticated else None
        work_order.plan.execution_notes = outcome_notes
        work_order.plan.save()

        # Log action
        AuditLog.objects.create(
            action_type='WO_COMPLETE',
            user=request.user if request.user.is_authenticated else None,
            object_id=work_order.id,
            details_json={
                'wo_number': work_order.wo_number,
                'outcome': outcome_notes[:100]
            },
            success=True
        )

        serializer = WorkOrderSerializer(work_order)
        return Response(serializer.data)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoints for audit logs (read-only).

    Endpoints:
        GET /api/ops/audit/ - List all audit logs
        GET /api/ops/audit/{id}/ - Retrieve specific log
    """

    queryset = AuditLog.objects.all().select_related('user')
    serializer_class = AuditLogSerializer
    filterset_fields = ['action_type', 'user', 'success']
    ordering = ['-timestamp']
