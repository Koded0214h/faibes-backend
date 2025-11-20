from django.contrib import admin
from .models import Alert, AlertNotification, SafetyNetworkMember, WebSocketConnection, PanicButtonPress

@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ['journey', 'alert_type', 'status', 'severity', 'created_at']
    list_filter = ['alert_type', 'status', 'severity', 'created_at']
    search_fields = ['journey__user__full_name', 'triggered_by__full_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('journey', 'alert_type', 'status', 'severity')
        }),
        ('Trigger Information', {
            'fields': ('triggered_by', 'trigger_data')
        }),
        ('Location Context', {
            'fields': ('location_lat', 'location_lng', 'location_address')
        }),
        ('Device Context', {
            'fields': ('battery_level', 'network_strength', 'device_info')
        }),
        ('Resolution', {
            'fields': ('resolved_by', 'resolved_at', 'resolution_notes', 'acknowledged_at')
        }),
    )

@admin.register(AlertNotification)
class AlertNotificationAdmin(admin.ModelAdmin):
    list_display = ['alert', 'notification_type', 'status', 'recipient_phone', 'created_at']
    list_filter = ['notification_type', 'status', 'created_at']
    search_fields = ['alert__journey__user__full_name', 'recipient_phone']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(SafetyNetworkMember)
class SafetyNetworkMemberAdmin(admin.ModelAdmin):
    list_display = ['user', 'member_phone', 'member_name', 'is_active', 'is_primary']
    list_filter = ['is_active', 'is_primary', 'created_at']
    search_fields = ['user__full_name', 'member_phone', 'member_name']

@admin.register(WebSocketConnection)
class WebSocketConnectionAdmin(admin.ModelAdmin):
    list_display = ['user', 'connection_id', 'is_active', 'connected_at', 'last_activity']
    list_filter = ['is_active', 'connected_at']
    search_fields = ['user__full_name', 'connection_id']
    readonly_fields = ['connected_at', 'last_activity', 'disconnected_at']

@admin.register(PanicButtonPress)
class PanicButtonPressAdmin(admin.ModelAdmin):
    list_display = ['user', 'journey', 'press_count', 'is_emergency', 'is_cancelled', 'created_at']
    list_filter = ['is_emergency', 'is_cancelled', 'created_at']
    search_fields = ['user__full_name', 'journey__destination_address']
    readonly_fields = ['created_at']