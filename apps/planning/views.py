"""
API views for Planning app.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import MitigationPlan
from .serializers import (
    MitigationPlanSerializer,
    MitigationPlanListSerializer,
    PlanApprovalSerializer
)
from .services.mitigation_simulator import MitigationSimulator, BulkMitigationPlanner
from apps.risk.models import RiskAssessment


class MitigationPlanViewSet(viewsets.ModelViewSet):
    """
    API endpoints for mitigation plans.

    Endpoints:
        GET /api/plans/plans/ - List all plans
        GET /api/plans/plans/{id}/ - Retrieve specific plan
        POST /api/plans/plans/generate/ - Generate plans for risk assessment
        POST /api/plans/plans/generate_all/ - Generate plans for all high-risk transformers
        POST /api/plans/plans/{id}/approve/ - Approve or reject a plan
        PATCH /api/plans/plans/{id}/ - Update plan (status, notes, etc.)
    """

    queryset = MitigationPlan.objects.all().select_related(
        'assessment',
        'assessment__transformer',
        'assessment__forecast',
        'approved_by',
        'executed_by'
    )

    filterset_fields = ['status', 'assessment__transformer']
    ordering = ['-generated_at']

    def get_serializer_class(self):
        """Use lightweight serializer for list views."""
        if self.action == 'list':
            return MitigationPlanListSerializer
        return MitigationPlanSerializer

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """
        Generate mitigation plans for a specific risk assessment.

        POST /api/plans/plans/generate/
        Body: {
            "assessment_id": 1,
            "max_plans": 3  # optional, default 3
        }

        Returns:
            List of generated MitigationPlan instances
        """
        assessment_id = request.data.get('assessment_id')
        max_plans = request.data.get('max_plans', 3)

        if not assessment_id:
            return Response(
                {'error': 'assessment_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            assessment = get_object_or_404(RiskAssessment, pk=assessment_id)

            # Generate plans
            simulator = MitigationSimulator()
            plans = simulator.generate_plans(assessment, max_plans=max_plans)

            # Save plans
            for plan in plans:
                plan.save()

            serializer = MitigationPlanSerializer(plans, many=True)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Plan generation failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def generate_all(self, request):
        """
        Generate plans for all high-risk transformers.

        POST /api/plans/plans/generate_all/
        Body: {
            "min_risk_score": 0.7  # optional, default 0.7
        }

        Returns:
            {
                'successful': count,
                'failed': count,
                'total_attempted': count,
                'plans_created': count
            }
        """
        min_risk_score = request.data.get('min_risk_score', 0.7)

        try:
            bulk_planner = BulkMitigationPlanner()
            result = bulk_planner.plan_all_high_risk(min_risk_score=min_risk_score)

            # Count total plans created
            total_plans = sum(len(item['plans']) for item in result['successful'])

            return Response({
                'successful': result['success_count'],
                'failed': result['failure_count'],
                'total_attempted': result['total_attempted'],
                'plans_created': total_plans,
                'errors': result['failed']
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': f'Bulk plan generation failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Approve or reject a mitigation plan.

        POST /api/plans/plans/{id}/approve/
        Body: {
            "action": "approve" | "reject",
            "rejection_reason": "..." (required if rejecting)
        }

        Returns:
            Updated MitigationPlan instance
        """
        plan = self.get_object()

        serializer = PlanApprovalSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        action_type = serializer.validated_data['action']

        if action_type == 'approve':
            if plan.status == 'APPROVED':
                return Response(
                    {'error': 'Plan is already approved'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            plan.status = 'APPROVED'
            plan.approved_by = request.user
            plan.approved_at = timezone.now()
            plan.save()

            response_serializer = MitigationPlanSerializer(plan)
            return Response(response_serializer.data)

        elif action_type == 'reject':
            rejection_reason = serializer.validated_data.get('rejection_reason', '')

            if not rejection_reason:
                return Response(
                    {'error': 'rejection_reason is required for rejection'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            plan.status = 'REJECTED'
            plan.rejection_reason = rejection_reason
            plan.save()

            response_serializer = MitigationPlanSerializer(plan)
            return Response(response_serializer.data)

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """
        Mark plan as executed.

        POST /api/plans/plans/{id}/execute/
        Body: {
            "execution_notes": "..." (optional)
        }

        Returns:
            Updated MitigationPlan instance
        """
        plan = self.get_object()

        if plan.status != 'APPROVED':
            return Response(
                {'error': 'Only approved plans can be executed'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if plan.is_executed:
            return Response(
                {'error': 'Plan is already executed'},
                status=status.HTTP_400_BAD_REQUEST
            )

        plan.status = 'EXECUTED'
        plan.executed_by = request.user
        plan.executed_at = timezone.now()
        plan.execution_notes = request.data.get('execution_notes', '')
        plan.save()

        serializer = MitigationPlanSerializer(plan)
        return Response(serializer.data)
