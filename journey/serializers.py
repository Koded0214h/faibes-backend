from rest_framework import serializers
from .models import Journey, JourneyLocation, GroupJourney, Passenger, JourneyAlert
from users.serializers import UserProfileSerializer

class JourneyLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = JourneyLocation
        fields = [
            'id', 'latitude', 'longitude', 'accuracy', 'speed', 'heading',
            'battery_level', 'network_strength', 'timestamp'
        ]

class JourneyAlertSerializer(serializers.ModelSerializer):
    resolved_by_name = serializers.CharField(source='resolved_by.full_name', read_only=True)
    
    class Meta:
        model = JourneyAlert
        fields = [
            'id', 'alert_type', 'status', 'severity', 'trigger_data',
            'location_lat', 'location_lng', 'resolved_by', 'resolved_by_name',
            'resolved_at', 'resolution_notes', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class JourneySerializer(serializers.ModelSerializer):
    user_profile = UserProfileSerializer(source='user', read_only=True)
    current_location = serializers.SerializerMethodField()
    alerts = JourneyAlertSerializer(many=True, read_only=True)
    duration_minutes = serializers.SerializerMethodField()
    
    class Meta:
        model = Journey
        fields = [
            'id', 'journey_code', 'journey_type', 'status', 'user', 'user_profile',
            'driver_name', 'driver_phone', 'vehicle_plate', 'start_address',
            'destination_address', 'start_lat', 'start_lng', 'dest_lat', 'dest_lng',
            'scheduled_start', 'actual_start', 'estimated_arrival', 'actual_arrival',
            'safety_network', 'is_safety_active', 'current_location', 'alerts',
            'duration_minutes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user_profile']
    
    def get_current_location(self, obj):
        latest_location = obj.locations.order_by('-timestamp').first()
        if latest_location:
            return JourneyLocationSerializer(latest_location).data
        return None
    
    def get_duration_minutes(self, obj):
        if obj.actual_start and obj.actual_arrival:
            duration = obj.actual_arrival - obj.actual_start
            return int(duration.total_seconds() / 60)
        return None

class CreateJourneySerializer(serializers.ModelSerializer):
    class Meta:
        model = Journey
        fields = [
            'journey_type', 'driver_name', 'driver_phone', 'vehicle_plate',
            'start_address', 'destination_address', 'start_lat', 'start_lng',
            'dest_lat', 'dest_lng', 'scheduled_start'
        ]
    
    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['user'] = request.user
        validated_data['safety_network'] = request.user.safety_network
        
        # Set actual start time if journey is starting immediately
        if validated_data.get('scheduled_start') is None:
            from django.utils import timezone
            validated_data['actual_start'] = timezone.now()
            validated_data['status'] = 'active'
        
        return super().create(validated_data)

class GroupJourneySerializer(serializers.ModelSerializer):
    journey = JourneySerializer(read_only=True)
    driver_profile = UserProfileSerializer(source='driver', read_only=True)
    passenger_count = serializers.IntegerField(source='current_passengers', read_only=True)
    
    class Meta:
        model = GroupJourney
        fields = [
            'id', 'journey', 'driver', 'driver_profile', 'vehicle_type',
            'vehicle_capacity', 'company_name', 'route_name', 'stops',
            'max_passengers', 'current_passengers', 'passenger_count',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class CreateGroupJourneySerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupJourney
        fields = [
            'vehicle_type', 'vehicle_capacity', 'company_name', 'route_name', 'stops',
            'max_passengers'
        ]
    
    def create(self, validated_data):
        request = self.context.get('request')
        
        # Create the base journey first
        journey_data = {
            'user': request.user,
            'journey_type': 'group',
            'driver_name': request.user.full_name,
            'driver_phone': request.user.phone,
            'start_address': 'Group Journey Start',
            'destination_address': validated_data['route_name'],
            'safety_network': request.user.safety_network,
            'status': 'scheduled'
        }
        
        journey = Journey.objects.create(**journey_data)
        validated_data['journey'] = journey
        validated_data['driver'] = request.user
        
        return super().create(validated_data)

class PassengerSerializer(serializers.ModelSerializer):
    user_profile = UserProfileSerializer(source='user', read_only=True)
    
    class Meta:
        model = Passenger
        fields = [
            'id', 'user', 'user_profile', 'boarding_stop', 'destination_stop',
            'is_checked_in', 'checked_in_at', 'emergency_contact_notified',
            'joined_at'
        ]
        read_only_fields = ['id', 'joined_at']

class JoinGroupJourneySerializer(serializers.Serializer):
    journey_code = serializers.CharField(max_length=6, required=True)
    boarding_stop = serializers.CharField(required=True)
    destination_stop = serializers.CharField(required=True)
    
    def validate_journey_code(self, value):
        try:
            journey = Journey.objects.get(journey_code=value, journey_type='group')
            self.context['journey'] = journey
        except Journey.DoesNotExist:
            raise serializers.ValidationError("Invalid journey code")
        return value

class LocationUpdateSerializer(serializers.ModelSerializer):
    journey_id = serializers.UUIDField(required=True)
    
    class Meta:
        model = JourneyLocation
        fields = [
            'journey_id', 'latitude', 'longitude', 'accuracy', 'speed', 'heading',
            'battery_level', 'network_strength'
        ]
    
    def validate_journey_id(self, value):
        try:
            journey = Journey.objects.get(id=value)
            self.context['journey'] = journey
        except Journey.DoesNotExist:
            raise serializers.ValidationError("Journey not found")
        return value

class JourneyStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Journey.JOURNEY_STATUS)
    
    def validate_status(self, value):
        valid_transitions = {
            'scheduled': ['active', 'cancelled'],
            'active': ['completed', 'emergency', 'cancelled'],
            'emergency': ['completed', 'cancelled'],
            'completed': [],
            'cancelled': [],
        }
        
        current_status = self.context['journey'].status
        if value not in valid_transitions.get(current_status, []):
            raise serializers.ValidationError(
                f"Cannot transition from {current_status} to {value}"
            )
        return value