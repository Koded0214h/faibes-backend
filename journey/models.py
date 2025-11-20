from django.db import models
import uuid
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()

class Journey(models.Model):
    JOURNEY_STATUS = [
        ('scheduled', 'Scheduled'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('emergency', 'Emergency'),
    ]
    
    JOURNEY_TYPE = [
        ('individual', 'Individual'),
        ('group', 'Group'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Journey Identification
    journey_code = models.CharField(max_length=6, unique=True, blank=True)  # For group journeys
    journey_type = models.CharField(max_length=20, choices=JOURNEY_TYPE, default='individual')
    status = models.CharField(max_length=20, choices=JOURNEY_STATUS, default='scheduled')
    
    # User & Driver Information
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='journeys')
    driver_name = models.CharField(max_length=255, blank=True)  # For Bolt/Uber trips
    driver_phone = models.CharField(max_length=20, blank=True)
    vehicle_plate = models.CharField(max_length=20, blank=True)
    
    # Route Information
    start_address = models.TextField()
    destination_address = models.TextField()
    start_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    start_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    dest_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    dest_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Timing
    scheduled_start = models.DateTimeField(default=timezone.now)
    actual_start = models.DateTimeField(null=True, blank=True)
    estimated_arrival = models.DateTimeField(null=True, blank=True)
    actual_arrival = models.DateTimeField(null=True, blank=True)
    
    # Safety
    safety_network = models.JSONField(default=list)  # Copy of user's safety network at journey start
    is_safety_active = models.BooleanField(default=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'journeys'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.full_name} - {self.destination_address} ({self.status})"
    
    def save(self, *args, **kwargs):
        if not self.journey_code and self.journey_type == 'group':
            self.journey_code = self.generate_journey_code()
        super().save(*args, **kwargs)
    
    def generate_journey_code(self):
        """Generate a unique 6-digit journey code"""
        import random
        while True:
            code = str(random.randint(100000, 999999))
            if not Journey.objects.filter(journey_code=code).exists():
                return code

class JourneyLocation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    journey = models.ForeignKey(Journey, on_delete=models.CASCADE, related_name='locations')
    
    # Location Data
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    accuracy = models.FloatField(null=True, blank=True)  # GPS accuracy in meters
    speed = models.FloatField(null=True, blank=True)  # km/h
    heading = models.FloatField(null=True, blank=True)  # degrees from north
    
    # Additional Context
    battery_level = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        null=True, blank=True
    )
    network_strength = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        null=True, blank=True
    )
    
    timestamp = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'journey_locations'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.journey.user.full_name} - {self.timestamp}"

class GroupJourney(models.Model):
    """For bus/group travel with multiple passengers"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Journey Information
    journey = models.OneToOneField(Journey, on_delete=models.CASCADE, related_name='group_journey')
    driver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='driven_journeys')
    
    # Vehicle Information
    vehicle_type = models.CharField(max_length=100)  # e.g., "Bus", "Minivan"
    vehicle_capacity = models.IntegerField()
    company_name = models.CharField(max_length=255, blank=True)
    
    # Route Details
    route_name = models.CharField(max_length=255)  # e.g., "Lagos-Abuja"
    stops = models.JSONField(default=list, blank=True)  # List of stops along the route
    
    # Passenger Management
    max_passengers = models.IntegerField(default=50)
    current_passengers = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'group_journeys'
        verbose_name_plural = 'Group Journeys'

    def __str__(self):
        return f"{self.route_name} - {self.driver.full_name}"

class Passenger(models.Model):
    """Passengers in a group journey"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group_journey = models.ForeignKey(GroupJourney, on_delete=models.CASCADE, related_name='passengers')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_journeys')
    
    # Boarding information
    boarding_stop = models.CharField(max_length=255)
    destination_stop = models.CharField(max_length=255)
    
    # Status
    is_checked_in = models.BooleanField(default=False)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    
    # Safety
    emergency_contact_notified = models.BooleanField(default=False)
    
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'passengers'
        unique_together = ['group_journey', 'user']

    def __str__(self):
        return f"{self.user.full_name} - {self.group_journey.route_name}"

class JourneyAlert(models.Model):
    ALERT_TYPES = [
        ('panic', 'Panic Button'),
        ('voice', 'Voice Trigger'),
        ('motion', 'Motion Detection'),
        ('deviation', 'Route Deviation'),
        ('battery', 'Low Battery'),
        ('network', 'Poor Network'),
        ('duration', 'Long Duration'),
    ]
    
    ALERT_STATUS = [
        ('active', 'Active'),
        ('resolved', 'Resolved'),
        ('false_alarm', 'False Alarm'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    journey = models.ForeignKey(Journey, on_delete=models.CASCADE, related_name='journey_alerts')
    
    # Alert Information
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    status = models.CharField(max_length=20, choices=ALERT_STATUS, default='active')
    severity = models.CharField(max_length=20, default='medium')  # low, medium, high, critical
    
    # Context Data
    trigger_data = models.JSONField(default=dict, blank=True)  # Additional context like voice confidence, motion data
    location_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Resolution
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'journey_alerts'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.journey.user.full_name} - {self.alert_type} - {self.status}"