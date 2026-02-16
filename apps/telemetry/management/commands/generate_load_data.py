"""
Management command to generate synthetic transformer load data.

This creates realistic 7 days of hourly load readings for all transformers:
- Daily peaks at 18:00 (6 PM) for residential load
- Weekend load patterns differ from weekdays
- Some transformers approach 85-95% during peaks (realistic stress scenarios)
- Temperature correlation with load
- Random variation to simulate real-world data
"""

import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.assets.models import Transformer
from apps.telemetry.models import TransformerLoad


class Command(BaseCommand):
    help = 'Generate synthetic transformer load data for demonstration (7 days of hourly readings)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days of data to generate (default: 7)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing load data before generating new data'
        )

    def handle(self, *args, **options):
        days = options['days']
        clear_existing = options['clear']

        if clear_existing:
            self.stdout.write(self.style.WARNING('Clearing existing load data...'))
            TransformerLoad.objects.all().delete()

        # Get all transformers
        transformers = Transformer.objects.filter(is_active=True)

        if not transformers.exists():
            self.stdout.write(
                self.style.ERROR(
                    'No transformers found! Run "python manage.py generate_grid_data" first.'
                )
            )
            return

        self.stdout.write(self.style.SUCCESS(f'Generating {days} days of load data for {transformers.count()} transformers...'))

        # Define transformer-specific load profiles (some will be high-risk)
        transformer_profiles = {}
        high_risk_transformers = ['T-07', 'T-04']  # These will show high load for demo

        for transformer in transformers:
            if transformer.name in high_risk_transformers:
                # High load profile (85-95% during peaks)
                base_load_pct = random.uniform(0.60, 0.70)  # 60-70% base
                peak_multiplier = random.uniform(1.35, 1.45)  # Results in 85-100% peak
            else:
                # Normal load profile (60-80% during peaks)
                base_load_pct = random.uniform(0.45, 0.55)  # 45-55% base
                peak_multiplier = random.uniform(1.35, 1.55)  # Results in 60-85% peak

            transformer_profiles[transformer.id] = {
                'base_load_pct': base_load_pct,
                'peak_multiplier': peak_multiplier
            }

        # Generate data
        now = timezone.now()
        start_time = now - timedelta(days=days)
        total_records = 0

        batch_records = []
        batch_size = 500  # Bulk create in batches for performance

        for hour_offset in range(days * 24):
            timestamp = start_time + timedelta(hours=hour_offset)
            hour_of_day = timestamp.hour
            day_of_week = timestamp.weekday()  # 0=Monday, 6=Sunday

            # Calculate time-of-day load factor
            load_factor = self._calculate_load_factor(hour_of_day, day_of_week)

            # Calculate ambient temperature (simulated)
            temp_c = self._calculate_temperature(hour_of_day, day_of_week)

            for transformer in transformers:
                profile = transformer_profiles[transformer.id]

                # Calculate load for this transformer at this time
                base_load = profile['base_load_pct'] * transformer.rated_kw
                time_adjusted_load = base_load * load_factor

                # Add random variation (±5%)
                variation = random.uniform(0.95, 1.05)
                final_load_kw = time_adjusted_load * variation

                # Add temperature effect (higher temp = higher load for cooling)
                if temp_c > 25:
                    temp_factor = 1.0 + ((temp_c - 25) * 0.01)  # 1% increase per degree above 25°C
                    final_load_kw *= temp_factor

                # Ensure load doesn't exceed transformer capacity significantly
                max_load_kw = transformer.rated_kw * 1.15  # Allow up to 115% overload
                final_load_kw = min(final_load_kw, max_load_kw)

                # Calculate load percentage
                load_pct = (final_load_kw / transformer.rated_kw) * 100

                # Create record
                record = TransformerLoad(
                    transformer=transformer,
                    timestamp=timestamp,
                    load_kw=round(final_load_kw, 2),
                    load_pct=round(load_pct, 2),
                    temp_c=round(temp_c, 1)
                )

                batch_records.append(record)
                total_records += 1

                # Bulk create when batch is full
                if len(batch_records) >= batch_size:
                    TransformerLoad.objects.bulk_create(batch_records, ignore_conflicts=True)
                    batch_records = []

            # Progress update every 24 hours
            if (hour_offset + 1) % 24 == 0:
                day_completed = (hour_offset + 1) // 24
                self.stdout.write(f'Generated data for day {day_completed}/{days}')

        # Create remaining records
        if batch_records:
            TransformerLoad.objects.bulk_create(batch_records, ignore_conflicts=True)

        # Summary
        self.stdout.write(self.style.SUCCESS('\n=== Load Data Generation Complete ==='))
        self.stdout.write(f'Total records created: {total_records}')
        self.stdout.write(f'Transformers: {transformers.count()}')
        self.stdout.write(f'Days: {days}')
        self.stdout.write(f'Hourly readings per transformer: {days * 24}')

        # Show high-risk transformers
        self.stdout.write(
            self.style.WARNING(
                f'\nHigh-risk transformers for demo: {", ".join(high_risk_transformers)}'
            )
        )

    def _calculate_load_factor(self, hour_of_day, day_of_week):
        """
        Calculate load factor based on time of day and day of week.

        Residential load pattern:
        - Low: 1:00-5:00 (0.5-0.6)
        - Morning ramp: 6:00-9:00 (0.7-0.9)
        - Midday: 10:00-16:00 (0.8-1.0)
        - Evening peak: 17:00-22:00 (1.2-1.5)
        - Night: 23:00-0:00 (0.7-0.8)
        """
        # Base pattern
        if 1 <= hour_of_day <= 5:
            base_factor = random.uniform(0.5, 0.6)
        elif 6 <= hour_of_day <= 9:
            base_factor = random.uniform(0.7, 0.9)
        elif 10 <= hour_of_day <= 16:
            base_factor = random.uniform(0.8, 1.0)
        elif 17 <= hour_of_day <= 22:
            # Evening peak - highest load
            peak_hour_factor = 1.0 + ((22 - hour_of_day) * 0.05)  # Peak at 18:00
            if hour_of_day == 18:
                base_factor = random.uniform(1.4, 1.5)  # Highest peak
            else:
                base_factor = random.uniform(1.2, 1.4) * peak_hour_factor
        else:
            base_factor = random.uniform(0.7, 0.8)

        # Weekend adjustment (lower load)
        if day_of_week in [5, 6]:  # Saturday, Sunday
            base_factor *= 0.85

        return base_factor

    def _calculate_temperature(self, hour_of_day, day_of_week):
        """
        Simulate ambient temperature in Celsius.

        Jordan (Amman) winter temperatures: 5-15°C
        Summer temperatures: 25-38°C
        Using summer temperatures for demo (higher load correlation)
        """
        # Base summer temperature pattern
        if 0 <= hour_of_day <= 6:
            # Coolest at dawn
            temp = random.uniform(23, 26)
        elif 7 <= hour_of_day <= 11:
            # Morning warming
            temp = random.uniform(26, 32)
        elif 12 <= hour_of_day <= 16:
            # Afternoon peak heat
            temp = random.uniform(33, 38)
        elif 17 <= hour_of_day <= 20:
            # Evening cooling
            temp = random.uniform(30, 34)
        else:
            # Night
            temp = random.uniform(25, 28)

        return temp
