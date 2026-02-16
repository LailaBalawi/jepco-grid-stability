"""
Test script for forecasting functionality.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from apps.assets.models import Transformer
from apps.forecasting.services.predictor import LoadForecaster, BulkForecaster

print("=" * 60)
print("JEPCO GRID - FORECASTING TEST")
print("=" * 60)

# Test 1: Single transformer forecast
print("\n[Test 1] Generating forecast for T-07...")
try:
    t7 = Transformer.objects.get(name='T-07')
    forecaster = LoadForecaster(lookback_days=7)
    forecast = forecaster.forecast(t7, hours_ahead=72)

    print(f"Transformer: {forecast.transformer.name}")
    print(f"Forecast horizon: {forecast.forecast_horizon_hours} hours")
    print(f"Algorithm: {forecast.algorithm}")
    print(f"Peak predicted: {forecast.peak_predicted_kw} kW ({forecast.peak_predicted_pct}%)")
    print(f"Peak time: {forecast.peak_time}")
    print(f"Total predictions: {len(forecast.predictions)}")
    print(f"Metadata: {forecast.metadata}")

    # Show first 5 predictions
    print("\nFirst 5 hourly predictions:")
    for i, pred in enumerate(forecast.predictions[:5]):
        print(f"  {i+1}. {pred['timestamp']}: {pred['predicted_kw']} kW ({pred['predicted_pct']}%) - Confidence: {pred['confidence']}")

    # Save to database
    forecast.save()
    print(f"\n[SUCCESS] Forecast saved to database (ID: {forecast.id})")

except ValueError as e:
    print(f"[ERROR] {e}")
except Exception as e:
    print(f"[ERROR] Unexpected error: {e}")

# Test 2: Bulk forecasting
print("\n" + "=" * 60)
print("[Test 2] Generating forecasts for all transformers...")
try:
    bulk_forecaster = BulkForecaster(lookback_days=7, hours_ahead=72)
    result = bulk_forecaster.forecast_all_transformers(save=True)

    print(f"\nResults:")
    print(f"  Total attempted: {result['total_attempted']}")
    print(f"  Successful: {result['success_count']}")
    print(f"  Failed: {result['failure_count']}")

    if result['successful']:
        print(f"\nSuccessful forecasts:")
        for forecast in result['successful']:
            status_indicator = "[HIGH RISK]" if forecast.peak_predicted_pct > 85 else "[NORMAL]"
            print(f"  {status_indicator} {forecast.transformer.name}: Peak {forecast.peak_predicted_pct}% at {forecast.peak_time.strftime('%Y-%m-%d %H:%M')}")

    if result['failed']:
        print(f"\nFailed forecasts:")
        for failure in result['failed']:
            print(f"  {failure['transformer'].name}: {failure['error']}")

    print(f"\n[SUCCESS] Bulk forecasting complete")

except Exception as e:
    print(f"[ERROR] Bulk forecasting failed: {e}")

print("\n" + "=" * 60)
print("[COMPLETE] All forecasting tests finished")
print("=" * 60)
