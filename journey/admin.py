from django.contrib import admin
from .models import Journey, JourneyLocation, GroupJourney, Passenger, JourneyAlert

# Register your models here.

@admin.register(Journey)
class JourneyAdmin(admin.ModelAdmin):
    list_display = ['user', 'destination_address', 'journey_type', 'status', 'created_at']
    list_filter = ['journey_type', 'status', 'created_at']
    search_fields = ['user__full_name', 'destination_address', 'journey_code']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'journey_type', 'journey_code', 'status')
        }),
        ('Driver & Vehicle', {
            'fields': ('driver_name', 'driver_phone', 'vehicle_plate')
        }),
        ('Route Information', {
            'fields': ('start_address', 'destination_address', 'start_lat', 'start_lng', 'dest_lat', 'dest_lng')
        }),
        ('Timing', {
            'fields': ('scheduled_start', 'actual_start', 'estimated_arrival', 'actual_arrival')
        }),
        ('Safety', {
            'fields': ('safety_network', 'is_safety_active')
        }),
    )

@admin.register(JourneyLocation)
class JourneyLocationAdmin(admin.ModelAdmin):
    list_display = ['journey', 'latitude', 'longitude', 'speed', 'timestamp']
    list_filter = ['timestamp']
    search_fields = ['journey__user__full_name']
    readonly_fields = ['timestamp']

@admin.register(GroupJourney)
class GroupJourneyAdmin(admin.ModelAdmin):
    list_display = ['route_name', 'driver', 'vehicle_type', 'current_passengers', 'max_passengers']
    list_filter = ['vehicle_type', 'created_at']
    search_fields = ['route_name', 'driver__full_name', 'company_name']

@admin.register(Passenger)
class PassengerAdmin(admin.ModelAdmin):
    list_display = ['user', 'group_journey', 'boarding_stop', 'destination_stop', 'is_checked_in']
    list_filter = ['is_checked_in', 'joined_at']
    search_fields = ['user__full_name', 'group_journey__route_name']

@admin.register(JourneyAlert)
class JourneyAlertAdmin(admin.ModelAdmin):
    list_display = ['journey', 'alert_type', 'status', 'severity', 'created_at']
    list_filter = ['alert_type', 'status', 'severity', 'created_at']
    search_fields = ['journey__user__full_name']
    readonly_fields = ['created_at', 'updated_at']
