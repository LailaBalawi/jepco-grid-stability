"""
Template views for dashboards and UI.
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from apps.assets.models import Substation, Feeder, Transformer
from apps.forecasting.models import LoadForecast
from apps.risk.models import RiskAssessment
from apps.planning.models import MitigationPlan
from apps.ops.models import WorkOrder, AuditLog


@login_required
def dashboard(request):
    """
    Main dashboard showing system overview and high-risk transformers.
    """
    # Get counts
    high_risk_assessments = RiskAssessment.objects.filter(risk_level='HIGH').select_related(
        'transformer',
        'transformer__feeder',
        'transformer__feeder__substation',
        'forecast'
    )[:10]

    low_risk_count = RiskAssessment.objects.filter(risk_level='LOW').count()
    medium_risk_count = RiskAssessment.objects.filter(risk_level='MEDIUM').count()
    high_risk_count = RiskAssessment.objects.filter(risk_level='HIGH').count()

    # Recent logs
    recent_logs = AuditLog.objects.all().select_related('user')[:10]

    # System stats
    context = {
        'high_risk_assessments': high_risk_assessments,
        'high_risk_count': high_risk_count,
        'medium_risk_count': medium_risk_count,
        'low_risk_count': low_risk_count,
        'total_forecasts': LoadForecast.objects.count(),
        'total_plans': MitigationPlan.objects.count(),
        'total_workorders': WorkOrder.objects.count(),
        'completed_workorders': WorkOrder.objects.filter(status='COMPLETED').count(),
        'recent_logs': recent_logs,
        'total_substations': Substation.objects.count(),
        'total_feeders': Feeder.objects.count(),
        'total_transformers': Transformer.objects.count(),
        'total_assessments': RiskAssessment.objects.count(),
        'total_logs': AuditLog.objects.count(),
    }

    return render(request, 'dashboard.html', context)


@login_required
def work_orders_view(request):
    """
    Work orders list view.
    """
    workorders = WorkOrder.objects.all().select_related(
        'plan',
        'plan__assessment',
        'plan__assessment__transformer'
    ).order_by('-created_at')

    context = {
        'workorders': workorders
    }

    return render(request, 'work_orders.html', context)
