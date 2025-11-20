from django.db import models
import uuid
from django.utils import timezone
from django.contrib.auth import get_user_model
from journey.models import Journey

User = get_user_model()

class Alert(models.Model):
    ALERT_TYPES = [
        ('panic_button', 'Panic Button'),
        ('voice_trigger', 'Voice Trigger'),
        ('motion_crash', 'Motion/Crash Detection'),
        ('route_deviation', 'Route Deviation'),
        ('no_movement', 'No Movement'),
        ('geofence_breach', 'Geofence Breach'),
        ('low_battery', 'Low Battery'),
        ('poor_network', 'Poor Network'),
        ('long_duration', 'Long Journey Duration'),
        ('manual', 'Manual Alert'),
    ]
    
    ALERT_STATUS = [
        ('triggered', 'Triggered'),
        ('verified', 'Verified'),
        ('notified', 'Notified'),
        ('resolved', 'Resolved'),
        ('false_alarm', 'False Alarm'),
        ('cancelled', 'Cancelled'),
    ]
    
    SEVERITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Core Alert Information
    journey = models.ForeignKey(Journey, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    status = models.CharField(max_length=20, choices=ALERT_STATUS, default='triggered')
    severity = models.CharField(max_length=20, choices=SEVERITY_LEVELS, default='high')
    
    # Trigger Information
    trigger_data = models.JSONField(default=dict, blank=True)  # Voice confidence, motion data, etc.
    triggered_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='triggered_alerts')
    
    # Location Context
    location_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_address = models.TextField(blank=True)
    
    # Device Context
    battery_level = models.IntegerField(null=True, blank=True)
    network_strength = models.IntegerField(null=True, blank=True)
    device_info = models.JSONField(default=dict, blank=True)
    
    # Resolution Information
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_alerts')
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'alerts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['journey', 'status']),
            models.Index(fields=['status', 'severity']),
        ]

    def __str__(self):
        return f"{self.journey.user.full_name} - {self.alert_type} - {self.severity}"

class AlertNotification(models.Model):
    NOTIFICATION_TYPES = [
        ('websocket', 'WebSocket'),
        ('sms', 'SMS'),
        ('whatsapp', 'WhatsApp'),
        ('push', 'Push Notification'),
        ('email', 'Email'),
    ]
    
    NOTIFICATION_STATUS = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('read', 'Read'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    alert = models.ForeignKey(Alert, on_delete=models.CASCADE, related_name='notifications')
    
    # Recipient Information
    recipient_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    recipient_phone = models.CharField(max_length=20, blank=True)
    recipient_email = models.EmailField(blank=True)
    
    # Notification Details
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    status = models.CharField(max_length=20, choices=NOTIFICATION_STATUS, default='pending')
    message = models.TextField()
    
    # Delivery Information
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    # Provider Information (for SMS/WhatsApp)
    provider_message_id = models.CharField(max_length=255, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'alert_notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.alert.alert_type} -> {self.recipient_phone or self.recipient_user}"

class SafetyNetworkMember(models.Model):
    """Track safety network members and their notification preferences"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='safety_network_members')
    member_phone = models.CharField(max_length=20)
    member_name = models.CharField(max_length=255, blank=True)
    
    # Notification Preferences
    receive_sms = models.BooleanField(default=True)
    receive_whatsapp = models.BooleanField(default=True)
    receive_push = models.BooleanField(default=True)
    
    # Relationship
    relationship = models.CharField(max_length=100, blank=True)
    is_primary = models.BooleanField(default=False)
    
    # Status
    is_active = models.BooleanField(default=True)
    last_notified = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'safety_network_members'
        unique_together = ['user', 'member_phone']

    def __str__(self):
        return f"{self.member_name or self.member_phone} - {self.user.full_name}"

class WebSocketConnection(models.Model):
    """Track active WebSocket connections for real-time updates"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='websocket_connections')
    connection_id = models.CharField(max_length=255, unique=True)
    
    # Connection Information
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    # Subscription Information
    subscribed_journeys = models.JSONField(default=list, blank=True)  # List of journey IDs
    subscribed_users = models.JSONField(default=list, blank=True)  # List of user IDs for safety network
    
    # Status
    is_active = models.BooleanField(default=True)
    connected_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    disconnected_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'websocket_connections'
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['connection_id']),
        ]

    def __str__(self):
        return f"{self.user.full_name} - {self.connection_id}"

class PanicButtonPress(models.Model):
    """Track manual panic button presses"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    journey = models.ForeignKey(Journey, on_delete=models.CASCADE, related_name='panic_presses')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='panic_presses')
    
    # Press Information
    press_count = models.IntegerField(default=1)
    press_duration = models.FloatField(null=True, blank=True)  # Seconds
    is_emergency = models.BooleanField(default=True)
    
    # Context
    location_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    battery_level = models.IntegerField(null=True, blank=True)
    
    # Cancellation
    is_cancelled = models.BooleanField(default=False)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'panic_button_presses'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.full_name} - {self.created_at}"