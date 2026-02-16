from django.contrib import admin
from .models import RiskAssessment


@admin.register(RiskAssessment)
class RiskAssessmentAdmin(admin.ModelAdmin):
    """
    Admin interface for Risk Assessment model.

    Displays risk scores with color-coded levels and filtering options.
    """

    list_display = [
        'id',
        'transformer',
        'risk_score',
        'risk_level',
        'overload_pct',
        'confidence',
        'peak_time_display',
        'assessed_at',
        'requires_action'
    ]

    list_filter = [
        'risk_level',
        'assessed_at',
        'transformer__feeder__substation'
    ]

    search_fields = [
        'transformer__name',
        'transformer__feeder__name'
    ]

    readonly_fields = [
        'assessed_at',
        'risk_score',
        'overload_pct',
        'confidence',
        'risk_components',
        'reasons_json',
        'risk_level'
    ]

    fieldsets = (
        ('Assessment Information', {
            'fields': (
                'transformer',
                'forecast',
                'assessed_at',
                'time_window_start',
                'time_window_end'
            )
        }),
        ('Risk Scores', {
            'fields': (
                'risk_score',
                'risk_level',
                'overload_pct',
                'confidence',
                'risk_components'
            )
        }),
        ('Explanation', {
            'fields': (
                'reasons_json',
            ),
            'classes': ('collapse',)
        })
    )

    date_hierarchy = 'assessed_at'
    ordering = ['-risk_score', '-assessed_at']

    def peak_time_display(self, obj):
        """Display peak time from forecast."""
        return obj.forecast.peak_time.strftime('%Y-%m-%d %H:%M')
    peak_time_display.short_description = 'Peak Time'

    def requires_action(self, obj):
        """Display action requirement status."""
        return obj.requires_action
    requires_action.boolean = True
    requires_action.short_description = 'Action Required'
