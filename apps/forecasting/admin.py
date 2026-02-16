from django.contrib import admin
from .models import LoadForecast


@admin.register(LoadForecast)
class LoadForecastAdmin(admin.ModelAdmin):
    """
    Admin interface for LoadForecast model.

    Displays forecast metadata and allows filtering by transformer and algorithm.
    Predictions JSON is read-only for safety.
    """

    list_display = [
        'id',
        'transformer',
        'forecast_generated_at',
        'forecast_horizon_hours',
        'peak_predicted_kw',
        'peak_predicted_pct',
        'peak_time',
        'algorithm'
    ]

    list_filter = [
        'algorithm',
        'forecast_generated_at',
        'transformer__feeder__substation'
    ]

    search_fields = [
        'transformer__name',
        'transformer__feeder__name'
    ]

    readonly_fields = [
        'forecast_generated_at',
        'predictions',
        'metadata'
    ]

    fieldsets = (
        ('Forecast Information', {
            'fields': (
                'transformer',
                'forecast_generated_at',
                'forecast_horizon_hours',
                'algorithm'
            )
        }),
        ('Peak Predictions', {
            'fields': (
                'peak_predicted_kw',
                'peak_predicted_pct',
                'peak_time'
            )
        }),
        ('Detailed Data', {
            'fields': (
                'predictions',
                'metadata'
            ),
            'classes': ('collapse',)
        })
    )

    date_hierarchy = 'forecast_generated_at'
    ordering = ['-forecast_generated_at']
