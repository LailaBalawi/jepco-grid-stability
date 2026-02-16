"""
Django admin configuration for Assets app.
"""

from django.contrib import admin
from .models import Substation, Feeder, Transformer, Switch, TopologyLink


class FeederInline(admin.TabularInline):
    """Inline editor for Feeders within Substation admin"""
    model = Feeder
    extra = 1
    fields = ('name', 'voltage_level', 'rated_capacity_kw')


class TransformerInline(admin.TabularInline):
    """Inline editor for Transformers within Feeder admin"""
    model = Transformer
    extra = 1
    fields = ('name', 'rated_kva', 'cooling_type', 'install_year', 'is_active')


@admin.register(Substation)
class SubstationAdmin(admin.ModelAdmin):
    """Admin interface for Substations"""
    list_display = ('name', 'region', 'feeder_count', 'created_at')
    list_filter = ('region',)
    search_fields = ('name', 'region')
    inlines = [FeederInline]

    def feeder_count(self, obj):
        return obj.feeders.count()
    feeder_count.short_description = 'Feeders'


@admin.register(Feeder)
class FeederAdmin(admin.ModelAdmin):
    """Admin interface for Feeders"""
    list_display = ('name', 'substation', 'voltage_level', 'rated_capacity_kw', 'transformer_count')
    list_filter = ('substation', 'voltage_level')
    search_fields = ('name', 'substation__name')
    inlines = [TransformerInline]

    def transformer_count(self, obj):
        return obj.transformers.count()
    transformer_count.short_description = 'Transformers'


@admin.register(Transformer)
class TransformerAdmin(admin.ModelAdmin):
    """Admin interface for Transformers"""
    list_display = ('name', 'feeder', 'rated_kva', 'rated_kw_display', 'max_load_pct', 'cooling_type', 'is_active')
    list_filter = ('feeder__substation', 'feeder', 'cooling_type', 'is_active')
    search_fields = ('name', 'feeder__name')
    readonly_fields = ('created_at', 'updated_at', 'rated_kw_display')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'feeder', 'is_active')
        }),
        ('Capacity', {
            'fields': ('rated_kva', 'rated_kw_display', 'max_load_pct')
        }),
        ('Technical Details', {
            'fields': ('cooling_type', 'install_year')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def rated_kw_display(self, obj):
        return f"{obj.rated_kw:.2f} kW"
    rated_kw_display.short_description = 'Rated kW (0.9 PF)'


@admin.register(Switch)
class SwitchAdmin(admin.ModelAdmin):
    """Admin interface for Switches"""
    list_display = ('name', 'feeder', 'switch_type', 'status', 'location', 'last_operated')
    list_filter = ('feeder', 'switch_type', 'status')
    search_fields = ('name', 'location')
    readonly_fields = ('last_operated', 'created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'feeder', 'switch_type')
        }),
        ('Status', {
            'fields': ('status', 'last_operated')
        }),
        ('Location', {
            'fields': ('location',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TopologyLink)
class TopologyLinkAdmin(admin.ModelAdmin):
    """Admin interface for Topology Links"""
    list_display = ('from_transformer', 'to_transformer', 'link_type', 'max_transfer_kw', 'switch', 'is_active')
    list_filter = ('link_type', 'is_active')
    search_fields = ('from_transformer__name', 'to_transformer__name')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Connection', {
            'fields': ('from_transformer', 'to_transformer', 'link_type')
        }),
        ('Capacity & Control', {
            'fields': ('max_transfer_kw', 'switch', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
