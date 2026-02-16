"""
API views for Risk app.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import RiskAssessment
from .serializers import (
    RiskAssessmentSerializer,
    RiskAssessmentListSerializer,
    RiskExplanationSerializer
)
from .services.risk_scorer import RiskScorer, BulkRiskScorer
from apps.assets.models import Transformer


class RiskAssessmentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoints for risk assessments.

    Endpoints:
        GET /api/risk/assessments/ - List all risk assessments
        GET /api/risk/assessments/{id}/ - Retrieve specific assessment
        POST /api/risk/assessments/run/ - Run risk analysis for all transformers
        POST /api/risk/assessments/run_single/ - Run risk analysis for single transformer
        GET /api/risk/assessments/explain/{id}/ - Get detailed risk explanation
        GET /api/risk/assessments/high_risk/ - Get high-risk transformers only
    """

    queryset = RiskAssessment.objects.all().select_related(
        'transformer',
        'transformer__feeder',
        'transformer__feeder__substation',
        'forecast'
    )

    filterset_fields = ['transformer', 'risk_level']
    ordering = ['-risk_score', '-assessed_at']

    def get_serializer_class(self):
        """Use lightweight serializer for list views."""
        if self.action == 'list':
            return RiskAssessmentListSerializer
        return RiskAssessmentSerializer

    @action(detail=False, methods=['post'])
    def run(self, request):
        """
        Run risk analysis for all active transformers.

        POST /api/risk/assessments/run/
        Body: {} (optional parameters)

        Returns:
            {
                'successful': count,
                'failed': count,
                'total_attempted': count,
                'high_risk_count': count,
                'assessments': [list of assessment IDs]
            }
        """
        try:
            bulk_scorer = BulkRiskScorer()
            result = bulk_scorer.score_all_transformers()

            # Count high-risk assessments
            high_risk_count = len([a for a in result['successful'] if a.is_high_risk])

            return Response({
                'successful': result['success_count'],
                'failed': result['failure_count'],
                'total_attempted': result['total_attempted'],
                'high_risk_count': high_risk_count,
                'assessments': [a.id for a in result['successful']],
                'errors': result['failed']
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': f'Risk analysis failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def run_single(self, request):
        """
        Run risk analysis for a single transformer.

        POST /api/risk/assessments/run_single/
        Body: {
            "transformer_id": 1
        }

        Returns:
            RiskAssessment instance
        """
        transformer_id = request.data.get('transformer_id')

        if not transformer_id:
            return Response(
                {'error': 'transformer_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            transformer = get_object_or_404(Transformer, pk=transformer_id)

            # Get latest forecast
            from apps.forecasting.models import LoadForecast
            forecast = LoadForecast.objects.filter(
                transformer=transformer
            ).order_by('-forecast_generated_at').first()

            if not forecast:
                return Response(
                    {'error': f'No forecast available for transformer {transformer.name}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Generate risk assessment
            scorer = RiskScorer()
            assessment = scorer.score_transformer(transformer, forecast)

            serializer = RiskAssessmentSerializer(assessment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'error': f'Risk analysis failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def explain(self, request, pk=None):
        """
        Get detailed risk explanation for chart visualization.

        GET /api/risk/assessments/{id}/explain/

        Returns:
            Detailed breakdown of risk components with weighted contributions
        """
        assessment = self.get_object()

        explanation_data = {
            'transformer_name': assessment.transformer.name,
            'risk_score': assessment.risk_score,
            'risk_level': assessment.risk_level,
            'overload_component': assessment.risk_components.get('overload', 0),
            'thermal_component': assessment.risk_components.get('thermal', 0),
            'cascading_component': assessment.risk_components.get('cascading', 0),
            'overload_contribution': float(assessment.risk_components.get('overload', 0)) * 0.6,
            'thermal_contribution': float(assessment.risk_components.get('thermal', 0)) * 0.2,
            'cascading_contribution': float(assessment.risk_components.get('cascading', 0)) * 0.2,
            'reasons': assessment.reasons_json
        }

        serializer = RiskExplanationSerializer(explanation_data)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def high_risk(self, request):
        """
        Get only high-risk assessments (risk_score >= 0.7).

        GET /api/risk/assessments/high_risk/

        Returns:
            List of high-risk assessments
        """
        high_risk_assessments = self.queryset.filter(risk_level='HIGH')

        serializer = RiskAssessmentListSerializer(high_risk_assessments, many=True)
        return Response(serializer.data)
