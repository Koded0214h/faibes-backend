from rest_framework import serializers
from .models import Alert, AlertNotification, SafetyNetworkMember, PanicButtonPress
from journey.serializers import JourneySerializer
from users.serializers import UserProfileSerializer
from datetime import timezone

class AlertNotificationSerializer(serializers.ModelSerializer):
    recipient_name = serializers.CharField(source='recipient_user.full_name', read_only=True)
    
    class Meta:
        model = AlertNotification
        fields = [
            'id', 'notification_type', 'status', 'message',
            'recipient_user', 'recipient_name', 'recipient_phone',
            'sent_at', 'delivered_at', 'read_at', 'error_message',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class AlertSerializer(serializers.ModelSerializer):
    journey_info = JourneySerializer(source='journey', read_only=True)
    triggered_by_name = serializers.CharField(source='triggered_by.full_name', read_only=True)
    resolved_by_name = serializers.CharField(source='resolved_by.full_name', read_only=True)
    notifications = AlertNotificationSerializer(many=True, read_only=True)
    
    class Meta:
        model = Alert
        fields = [
            'id', 'journey', 'journey_info', 'alert_type', 'status', 'severity',
            'trigger_data', 'triggered_by', 'triggered_by_name',
            'location_lat', 'location_lng', 'location_address',
            'battery_level', 'network_strength', 'device_info',
            'resolved_by', 'resolved_by_name', 'resolved_at', 'resolution_notes',
            'acknowledged_at', 'notifications', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class CreateAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = [
            'journey', 'alert_type', 'severity', 'trigger_data',
            'location_lat', 'location_lng', 'location_address',
            'battery_level', 'network_strength', 'device_info'
        ]
    
    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['triggered_by'] = request.user
        return super().create(validated_data)

class SafetyNetworkMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = SafetyNetworkMember
        fields = [
            'id', 'member_phone', 'member_name', 'receive_sms',
            'receive_whatsapp', 'receive_push', 'relationship',
            'is_primary', 'is_active', 'last_notified', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class CreateSafetyNetworkMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = SafetyNetworkMember
        fields = ['member_phone', 'member_name', 'relationship', 'is_primary']
    
    def validate_member_phone(self, value):
        # Basic phone validation
        if not value.startswith('+'):
            raise serializers.ValidationError(
                "Phone number must include country code (e.g., +2348012345678)"
            )
        return value

class PanicButtonPressSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    
    class Meta:
        model = PanicButtonPress
        fields = [
            'id', 'journey', 'user', 'user_name', 'press_count',
            'press_duration', 'is_emergency', 'location_lat', 'location_lng',
            'battery_level', 'is_cancelled', 'cancelled_at',
            'cancellation_reason', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class CreatePanicButtonPressSerializer(serializers.ModelSerializer):
    class Meta:
        model = PanicButtonPress
        fields = [
            'journey', 'press_count', 'press_duration', 'location_lat',
            'location_lng', 'battery_level'
        ]
    
    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['user'] = request.user
        return super().create(validated_data)

class AlertStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Alert.ALERT_STATUS)
    resolution_notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_status(self, value):
        valid_transitions = {
            'triggered': ['verified', 'false_alarm', 'cancelled'],
            'verified': ['notified', 'false_alarm', 'cancelled'],
            'notified': ['resolved', 'false_alarm'],
            'resolved': [],
            'false_alarm': [],
            'cancelled': [],
        }
        
        current_status = self.context['alert'].status
        if value not in valid_transitions.get(current_status, []):
            raise serializers.ValidationError(
                f"Cannot transition from {current_status} to {value}"
            )
        return value

class WebSocketMessageSerializer(serializers.Serializer):
    """Serializer for WebSocket messages"""
    type = serializers.CharField()  # message type: alert, location, status
    data = serializers.DictField()
    timestamp = serializers.DateTimeField(default=serializers.CreateOnlyDefault(lambda: timezone.now()))
    
    def validate_type(self, value):
        valid_types = ['alert', 'location_update', 'journey_status', 'panic_alert']
        if value not in valid_types:
            raise serializers.ValidationError(f"Invalid message type: {value}")
        return value