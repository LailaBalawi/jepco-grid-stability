"""
Django admin configuration for Telemetry app.
"""

from django.contrib import admin
from .models import TransformerLoad


@admin.register(TransformerLoad)
class TransformerLoadAdmin(admin.ModelAdmin):
    """Admin interface for Transformer Load Readings"""
    list_display = ('transformer', 'timestamp', 'load_kw', 'load_pct', 'temp_c', 'created_at')
    list_filter = ('transformer__feeder__substation', 'transformer__feeder', 'transformer', 'timestamp')
    search_fields = ('transformer__name',)
    readonly_fields = ('created_at', 'load_pct')
    date_hierarchy = 'timestamp'
    ordering = ('-timestamp',)

    fieldsets = (
        ('Measurement', {
            'fields': ('transformer', 'timestamp', 'load_kw', 'load_pct')
        }),
        ('Optional Readings', {
            'fields': ('voltage', 'temp_c'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        """Prevent manual addition through admin - use CSV upload or API"""
        return False
