"""
Verification script for forecasting data.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from apps.forecasting.models import LoadForecast

print("=" * 60)
print("FORECASTING DATA VERIFICATION")
print("=" * 60)

# Get all forecasts
forecasts = LoadForecast.objects.all().select_related('transformer')

print(f"\nTotal Forecasts: {forecasts.count()}")

print(f"\n[+] High-Risk Transformers (Predicted Peak > 85%):")
high_risk = forecasts.filter(peak_predicted_pct__gte=85).order_by('-peak_predicted_pct')

for forecast in high_risk:
    print(f"   Transformer: {forecast.transformer.name}")
    print(f"   Rated capacity: {forecast.transformer.rated_kw} kW")
    print(f"   Peak predicted: {forecast.peak_predicted_kw} kW ({forecast.peak_predicted_pct}%)")
    print(f"   Peak time: {forecast.peak_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"   Confidence: {forecast.predictions[0]['confidence']}")
    print(f"   Horizon: {forecast.forecast_horizon_hours} hours")
    print("")

print(f"[+] Sample Forecast Details (T-07):")
t7_forecast = forecasts.filter(transformer__name='T-07').first()
if t7_forecast:
    print(f"   Forecast ID: {t7_forecast.id}")
    print(f"   Generated at: {t7_forecast.forecast_generated_at}")
    print(f"   Algorithm: {t7_forecast.algorithm}")
    print(f"   Predictions count: {len(t7_forecast.predictions)}")
    print(f"   Metadata: {t7_forecast.metadata}")

    # Show predictions around peak time
    print(f"\n   Predictions near peak (hours 47-49 of 72):")
    for i in range(47, 50):
        if i < len(t7_forecast.predictions):
            pred = t7_forecast.predictions[i]
            print(f"      Hour {i+1}: {pred['predicted_kw']} kW ({pred['predicted_pct']}%)")

print("\n" + "=" * 60)
print("[SUCCESS] Forecasting verification complete!")
print("=" * 60)
