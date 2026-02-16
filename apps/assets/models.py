"""
Models for JEPCO Grid Assets.

This module contains models for the physical grid infrastructure:
- Substations
- Feeders
- Transformers
- Switches
- Topology Links (connections between transformers)
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Substation(models.Model):
    """
    Represents a power substation in the JEPCO grid.

    A substation is a facility that transforms voltage from high to low, or vice versa.
    It contains multiple feeders that distribute power to transformers.
    """
    name = models.CharField(max_length=100, unique=True, help_text="Substation name (e.g., SS-01)")
    region = models.CharField(max_length=100, help_text="Geographic region")
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
        help_text="Latitude coordinate for mapping"
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
        help_text="Longitude coordinate for mapping"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Substation"
        verbose_name_plural = "Substations"

    def __str__(self):
        return f"{self.name} ({self.region})"


class Feeder(models.Model):
    """
    Represents a feeder line from a substation.

    Feeders distribute power from substations to distribution transformers.
    Typically operates at medium voltage (11kV or 33kV).
    """
    substation = models.ForeignKey(
        Substation, on_delete=models.CASCADE, related_name='feeders',
        help_text="Parent substation"
    )
    name = models.CharField(max_length=100, help_text="Feeder name (e.g., FDR-A)")
    voltage_level = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Operating voltage level in kV"
    )
    rated_capacity_kw = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Rated capacity in kilowatts"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['substation__name', 'name']
        unique_together = ('substation', 'name')
        verbose_name = "Feeder"
        verbose_name_plural = "Feeders"

    def __str__(self):
        return f"{self.name} ({self.substation.name})"


class Transformer(models.Model):
    """
    Represents a distribution transformer.

    Transformers step down voltage for end users (residential/commercial).
    This is where we monitor load and predict overload risk.
    """
    COOLING_TYPES = [
        ('ONAN', 'Oil Natural Air Natural'),
        ('ONAF', 'Oil Natural Air Forced'),
        ('OFAF', 'Oil Forced Air Forced'),
    ]

    feeder = models.ForeignKey(
        Feeder, on_delete=models.CASCADE, related_name='transformers',
        help_text="Parent feeder"
    )
    name = models.CharField(
        max_length=100, unique=True,
        help_text="Transformer name (e.g., T-01)"
    )
    rated_kva = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Rated capacity in kVA"
    )
    max_load_pct = models.IntegerField(
        default=90,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Safe operating limit as percentage of rated capacity"
    )
    cooling_type = models.CharField(
        max_length=50, choices=COOLING_TYPES,
        help_text="Cooling system type"
    )
    install_year = models.IntegerField(
        validators=[MinValueValidator(1900), MaxValueValidator(2100)],
        help_text="Year of installation"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether transformer is currently in service"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['feeder__substation__name', 'feeder__name', 'name']
        verbose_name = "Transformer"
        verbose_name_plural = "Transformers"

    def __str__(self):
        return f"{self.name} ({self.rated_kva} kVA)"

    @property
    def rated_kw(self):
        """Convert kVA to kW assuming 0.9 power factor"""
        return float(self.rated_kva) * 0.9


class Switch(models.Model):
    """
    Represents a switch in the distribution network.

    Switches control power flow and enable load transfer between circuits.
    Can be normally open (NO) or normally closed (NC).
    """
    SWITCH_TYPES = [
        ('NO', 'Normally Open'),
        ('NC', 'Normally Closed'),
    ]

    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('CLOSED', 'Closed'),
        ('FAULT', 'Fault'),
        ('MAINTENANCE', 'Maintenance'),
    ]

    feeder = models.ForeignKey(
        Feeder, on_delete=models.CASCADE, related_name='switches',
        help_text="Parent feeder"
    )
    name = models.CharField(
        max_length=100, unique=True,
        help_text="Switch identifier (e.g., SW-03)"
    )
    switch_type = models.CharField(
        max_length=2, choices=SWITCH_TYPES,
        help_text="Normal operating state"
    )
    location = models.CharField(
        max_length=200,
        help_text="Physical location description"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='OPEN',
        help_text="Current operational status"
    )
    last_operated = models.DateTimeField(
        null=True, blank=True,
        help_text="Last time switch state was changed"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Switch"
        verbose_name_plural = "Switches"

    def __str__(self):
        return f"{self.name} ({self.get_switch_type_display()}, {self.status})"


class TopologyLink(models.Model):
    """
    Defines connections between transformers that enable load transfer.

    Topology links represent tie lines between normally separate circuits.
    They define which transformers can share load during emergencies.
    """
    LINK_TYPES = [
        ('tie_line', 'Tie Line'),
        ('backup_line', 'Backup Line'),
        ('emergency_tie', 'Emergency Tie'),
    ]

    from_transformer = models.ForeignKey(
        Transformer, on_delete=models.CASCADE, related_name='outgoing_links',
        help_text="Source transformer"
    )
    to_transformer = models.ForeignKey(
        Transformer, on_delete=models.CASCADE, related_name='incoming_links',
        help_text="Destination transformer"
    )
    link_type = models.CharField(
        max_length=50, choices=LINK_TYPES, default='tie_line',
        help_text="Type of connection"
    )
    max_transfer_kw = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Maximum safe power transfer in kW"
    )
    switch = models.ForeignKey(
        Switch, on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Switch controlling this link"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether link is available for load transfer"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['from_transformer__name', 'to_transformer__name']
        unique_together = ('from_transformer', 'to_transformer')
        verbose_name = "Topology Link"
        verbose_name_plural = "Topology Links"

    def __str__(self):
        return f"{self.from_transformer.name} → {self.to_transformer.name} ({self.max_transfer_kw} kW)"
