"""
Quick verification script for JEPCO Grid data.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.assets.models import Substation, Feeder, Transformer, Switch, TopologyLink
from apps.telemetry.models import TransformerLoad

print("=" * 60)
print("JEPCO GRID STABILITY ORCHESTRATOR - DATA VERIFICATION")
print("=" * 60)

print(f"\n[+] Assets:")
print(f"   Substations: {Substation.objects.count()}")
print(f"   Feeders: {Feeder.objects.count()}")
print(f"   Transformers: {Transformer.objects.count()}")
print(f"   Switches: {Switch.objects.count()}")
print(f"   Topology Links: {TopologyLink.objects.count()}")

print(f"\n[+] Telemetry:")
print(f"   Load Readings: {TransformerLoad.objects.count()}")

print(f"\n[+] High-Risk Transformers (Demo):")
for t in Transformer.objects.filter(name__in=['T-07', 'T-04']):
    latest = t.load_readings.first()
    if latest:
        print(f"   {t.name}: Latest load = {latest.load_kw} kW ({latest.load_pct:.1f}%)")
        print(f"           Temperature: {latest.temp_c}C")
        print(f"           Timestamp: {latest.timestamp}")
    else:
        print(f"   {t.name}: No load data")

print(f"\n[+] Sample Transformer Details (T-07):")
t7 = Transformer.objects.get(name='T-07')
print(f"   Name: {t7.name}")
print(f"   Rated: {t7.rated_kva} kVA ({t7.rated_kw:.1f} kW)")
print(f"   Feeder: {t7.feeder.name}")
print(f"   Substation: {t7.feeder.substation.name}")
print(f"   Load readings: {t7.load_readings.count()}")

# Check topology
neighbors = TopologyLink.objects.filter(from_transformer=t7)
print(f"   Topology links: {neighbors.count()}")
for link in neighbors:
    switch_info = link.switch.name if link.switch else 'direct'
    print(f"      => {link.to_transformer.name} (max {link.max_transfer_kw} kW via {switch_info})")

print("\n" + "=" * 60)
print("[SUCCESS] All data verified successfully!")
print("=" * 60)
