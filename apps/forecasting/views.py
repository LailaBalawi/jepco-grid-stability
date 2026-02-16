"""
API views for Forecasting app.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import LoadForecast
from .serializers import LoadForecastSerializer, LoadForecastListSerializer
from .services.predictor import LoadForecaster, BulkForecaster
from apps.assets.models import Transformer


class LoadForecastViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoints for load forecasts.

    Endpoints:
        GET /api/forecasting/forecasts/ - List all forecasts
        GET /api/forecasting/forecasts/{id}/ - Retrieve specific forecast
        POST /api/forecasting/forecasts/run/ - Generate forecast for transformer
        POST /api/forecasting/forecasts/run_all/ - Generate forecasts for all transformers
        GET /api/forecasting/forecasts/latest/{transformer_id}/ - Get latest forecast for transformer
    """

    queryset = LoadForecast.objects.all().select_related(
        'transformer',
        'transformer__feeder',
        'transformer__feeder__substation'
    )
    filterset_fields = ['transformer', 'algorithm']
    ordering = ['-forecast_generated_at']

    def get_serializer_class(self):
        """Use lightweight serializer for list views."""
        if self.action == 'list':
            return LoadForecastListSerializer
        return LoadForecastSerializer

    @action(detail=False, methods=['post'])
    def run(self, request):
        """
        Generate forecast for a specific transformer.

        POST /api/forecasting/forecasts/run/
        Body: {
            "transformer_id": 1,
            "hours_ahead": 72,  # optional, default 72
            "lookback_days": 7  # optional, default 7
        }

        Returns:
            LoadForecast instance (saved to database)
        """
        transformer_id = request.data.get('transformer_id')
        hours_ahead = request.data.get('hours_ahead', 72)
        lookback_days = request.data.get('lookback_days', 7)

        if not transformer_id:
            return Response(
                {'error': 'transformer_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            transformer = get_object_or_404(Transformer, pk=transformer_id)
            forecaster = LoadForecaster(lookback_days=lookback_days)
            forecast = forecaster.forecast(transformer, hours_ahead=hours_ahead)

            # Save to database
            forecast.save()

            serializer = LoadForecastSerializer(forecast)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Forecasting failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def run_all(self, request):
        """
        Generate forecasts for all active transformers.

        POST /api/forecasting/forecasts/run_all/
        Body: {
            "hours_ahead": 72,  # optional
            "lookback_days": 7,  # optional
            "save": true  # optional, default true
        }

        Returns:
            {
                'successful': count,
                'failed': count,
                'total_attempted': count,
                'forecasts': [list of forecast IDs],
                'errors': [list of error details]
            }
        """
        hours_ahead = request.data.get('hours_ahead', 72)
        lookback_days = request.data.get('lookback_days', 7)
        save = request.data.get('save', True)

        bulk_forecaster = BulkForecaster(
            lookback_days=lookback_days,
            hours_ahead=hours_ahead
        )

        result = bulk_forecaster.forecast_all_transformers(save=save)

        return Response({
            'successful': result['success_count'],
            'failed': result['failure_count'],
            'total_attempted': result['total_attempted'],
            'forecasts': [f.id for f in result['successful']],
            'errors': result['failed']
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='latest/(?P<transformer_id>[^/.]+)')
    def latest(self, request, transformer_id=None):
        """
        Get latest forecast for a transformer.

        GET /api/forecasting/forecasts/latest/{transformer_id}/

        Returns:
            Latest LoadForecast instance or 404 if none exists
        """
        forecast = LoadForecast.objects.filter(
            transformer_id=transformer_id
        ).order_by('-forecast_generated_at').first()

        if not forecast:
            return Response(
                {'error': f'No forecasts found for transformer {transformer_id}'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = LoadForecastSerializer(forecast)
        return Response(serializer.data)
