"""
Management command to generate synthetic grid topology data.

This creates realistic sample data for demonstration:
- 1 substation
- 3 feeders
- 10 transformers
- 8 topology links (tie lines between transformers)
"""

from django.core.management.base import BaseCommand
from apps.assets.models import Substation, Feeder, Transformer, Switch, TopologyLink


class Command(BaseCommand):
    help = 'Generate synthetic grid topology data for demonstration'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Clearing existing grid data...'))

        # Clear existing data
        TopologyLink.objects.all().delete()
        Switch.objects.all().delete()
        Transformer.objects.all().delete()
        Feeder.objects.all().delete()
        Substation.objects.all().delete()

        self.stdout.write(self.style.SUCCESS('Generating grid topology data...'))

        # Create Substation
        substation = Substation.objects.create(
            name='SS-01',
            region='Amman West',
            latitude=31.9539,
            longitude=35.9106
        )
        self.stdout.write(f'Created substation: {substation.name}')

        # Create Feeders
        feeders = []
        feeder_specs = [
            {'name': 'FDR-A', 'voltage_level': 33, 'capacity': 5000},
            {'name': 'FDR-B', 'voltage_level': 33, 'capacity': 4500},
            {'name': 'FDR-C', 'voltage_level': 11, 'capacity': 3000},
        ]

        for spec in feeder_specs:
            feeder = Feeder.objects.create(
                substation=substation,
                name=spec['name'],
                voltage_level=spec['voltage_level'],
                rated_capacity_kw=spec['capacity']
            )
            feeders.append(feeder)
            self.stdout.write(f'Created feeder: {feeder.name}')

        # Create Transformers
        transformers = []
        transformer_specs = [
            # FDR-A transformers
            {'name': 'T-01', 'feeder_idx': 0, 'kva': 500, 'cooling': 'ONAN', 'year': 2015},
            {'name': 'T-02', 'feeder_idx': 0, 'kva': 630, 'cooling': 'ONAN', 'year': 2018},
            {'name': 'T-03', 'feeder_idx': 0, 'kva': 500, 'cooling': 'ONAF', 'year': 2020},
            # FDR-B transformers
            {'name': 'T-04', 'feeder_idx': 1, 'kva': 800, 'cooling': 'ONAF', 'year': 2019},
            {'name': 'T-05', 'feeder_idx': 1, 'kva': 500, 'cooling': 'ONAN', 'year': 2016},
            {'name': 'T-06', 'feeder_idx': 1, 'kva': 630, 'cooling': 'ONAN', 'year': 2021},
            {'name': 'T-07', 'feeder_idx': 1, 'kva': 500, 'cooling': 'ONAN', 'year': 2017},  # High risk demo
            # FDR-C transformers
            {'name': 'T-08', 'feeder_idx': 2, 'kva': 400, 'cooling': 'ONAN', 'year': 2014},
            {'name': 'T-09', 'feeder_idx': 2, 'kva': 630, 'cooling': 'ONAF', 'year': 2022},
            {'name': 'T-10', 'feeder_idx': 2, 'kva': 500, 'cooling': 'ONAN', 'year': 2019},
        ]

        for spec in transformer_specs:
            transformer = Transformer.objects.create(
                feeder=feeders[spec['feeder_idx']],
                name=spec['name'],
                rated_kva=spec['kva'],
                max_load_pct=90,
                cooling_type=spec['cooling'],
                install_year=spec['year'],
                is_active=True
            )
            transformers.append(transformer)
            self.stdout.write(f'Created transformer: {transformer.name} ({transformer.rated_kva} kVA)')

        # Create Switches
        switches = []
        switch_specs = [
            {'name': 'SW-01', 'feeder_idx': 0, 'type': 'NO', 'location': 'Near T-01/T-02 junction', 'status': 'OPEN'},
            {'name': 'SW-02', 'feeder_idx': 0, 'type': 'NO', 'location': 'Near T-02/T-04 tie', 'status': 'OPEN'},
            {'name': 'SW-03', 'feeder_idx': 1, 'type': 'NO', 'location': 'Near T-07/T-09 tie', 'status': 'OPEN'},
            {'name': 'SW-04', 'feeder_idx': 1, 'type': 'NO', 'location': 'Near T-05/T-08 tie', 'status': 'OPEN'},
            {'name': 'SW-05', 'feeder_idx': 2, 'type': 'NC', 'location': 'FDR-C main', 'status': 'CLOSED'},
            {'name': 'SW-06', 'feeder_idx': 2, 'type': 'NO', 'location': 'Near T-09/T-10 tie', 'status': 'OPEN'},
        ]

        for spec in switch_specs:
            switch = Switch.objects.create(
                feeder=feeders[spec['feeder_idx']],
                name=spec['name'],
                switch_type=spec['type'],
                location=spec['location'],
                status=spec['status']
            )
            switches.append(switch)
            self.stdout.write(f'Created switch: {switch.name}')

        # Create Topology Links (tie lines between transformers)
        topology_links = [
            # Within FDR-A
            {'from_idx': 0, 'to_idx': 1, 'max_kw': 200, 'switch_idx': 0},  # T-01 ↔ T-02
            # Cross-feeder FDR-A to FDR-B
            {'from_idx': 1, 'to_idx': 3, 'max_kw': 250, 'switch_idx': 1},  # T-02 ↔ T-04
            {'from_idx': 2, 'to_idx': 4, 'max_kw': 180, 'switch_idx': None},  # T-03 ↔ T-05
            # Within FDR-B
            {'from_idx': 4, 'to_idx': 5, 'max_kw': 220, 'switch_idx': None},  # T-05 ↔ T-06
            # Cross-feeder FDR-B to FDR-C (IMPORTANT for demo: T-07 high risk → T-09 has capacity)
            {'from_idx': 6, 'to_idx': 8, 'max_kw': 300, 'switch_idx': 2},  # T-07 ↔ T-09
            {'from_idx': 4, 'to_idx': 7, 'max_kw': 150, 'switch_idx': 3},  # T-05 ↔ T-08
            # Within FDR-C
            {'from_idx': 8, 'to_idx': 9, 'max_kw': 200, 'switch_idx': 5},  # T-09 ↔ T-10
            # Additional tie
            {'from_idx': 3, 'to_idx': 6, 'max_kw': 280, 'switch_idx': None},  # T-04 ↔ T-07
        ]

        for link_spec in topology_links:
            from_transformer = transformers[link_spec['from_idx']]
            to_transformer = transformers[link_spec['to_idx']]
            switch = switches[link_spec['switch_idx']] if link_spec['switch_idx'] is not None else None

            link = TopologyLink.objects.create(
                from_transformer=from_transformer,
                to_transformer=to_transformer,
                link_type='tie_line',
                max_transfer_kw=link_spec['max_kw'],
                switch=switch,
                is_active=True
            )
            self.stdout.write(
                f'Created topology link: {from_transformer.name} => {to_transformer.name} '
                f'({link.max_transfer_kw} kW max)'
            )

        # Summary
        self.stdout.write(self.style.SUCCESS('\n=== Grid Topology Generated ==='))
        self.stdout.write(f'Substations: {Substation.objects.count()}')
        self.stdout.write(f'Feeders: {Feeder.objects.count()}')
        self.stdout.write(f'Transformers: {Transformer.objects.count()}')
        self.stdout.write(f'Switches: {Switch.objects.count()}')
        self.stdout.write(f'Topology Links: {TopologyLink.objects.count()}')
        self.stdout.write(self.style.SUCCESS('\nGrid topology data generated successfully!'))
        self.stdout.write(
            self.style.WARNING(
                '\nNote: T-07 is configured for high-risk demo scenarios with tie to T-09 (SW-03)'
            )
        )
