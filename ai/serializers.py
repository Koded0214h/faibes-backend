from rest_framework import serializers
from .models import VoiceDetectionEvent, AIChatSession, AIChatMessage, MotionDetectionEvent, AIFeedback
from journey.serializers import JourneySerializer
from users.serializers import UserProfileSerializer

class VoiceDetectionEventSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    journey_info = JourneySerializer(source='journey', read_only=True)
    
    class Meta:
        model = VoiceDetectionEvent
        fields = [
            'id', 'journey', 'journey_info', 'user', 'user_name', 'safe_word',
            'confidence', 'audio_duration', 'background_noise_level',
            'audio_snippet_url', 'audio_file', 'processing_time', 'model_version',
            'status', 'triggered_alert', 'user_feedback', 'feedback_notes',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class CreateVoiceDetectionEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoiceDetectionEvent
        fields = [
            'journey', 'safe_word', 'confidence', 'audio_duration',
            'background_noise_level', 'audio_snippet_url', 'processing_time',
            'model_version'
        ]
    
    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['user'] = request.user
        
        # Auto-trigger alert if confidence is high
        confidence = validated_data.get('confidence', 0)
        if confidence > 0.8:  # 80% confidence threshold
            validated_data['triggered_alert'] = True
        
        return super().create(validated_data)

class AIChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIChatMessage
        fields = [
            'id', 'message_type', 'content', 'ai_model', 
            'processing_time', 'tokens_used', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class AIChatSessionSerializer(serializers.ModelSerializer):
    user_profile = UserProfileSerializer(source='user', read_only=True)
    journey_info = JourneySerializer(source='journey', read_only=True)
    messages = AIChatMessageSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    
    class Meta:
        model = AIChatSession
        fields = [
            'id', 'user', 'user_profile', 'journey', 'journey_info', 'chat_type',
            'session_token', 'is_active', 'context_data', 'messages', 'last_message',
            'created_at', 'updated_at', 'ended_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_last_message(self, obj):
        last_message = obj.messages.order_by('-created_at').first()
        if last_message:
            return AIChatMessageSerializer(last_message).data
        return None

class CreateAIChatSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIChatSession
        fields = ['journey', 'chat_type', 'context_data']
    
    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['user'] = request.user
        
        # Generate session token
        import secrets
        validated_data['session_token'] = secrets.token_urlsafe(32)
        
        return super().create(validated_data)

class ChatMessageSerializer(serializers.Serializer):
    message = serializers.CharField(required=True)
    session_token = serializers.CharField(required=False)

class MotionDetectionEventSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    journey_info = JourneySerializer(source='journey', read_only=True)
    
    class Meta:
        model = MotionDetectionEvent
        fields = [
            'id', 'journey', 'journey_info', 'user', 'user_name', 'motion_type',
            'acceleration_x', 'acceleration_y', 'acceleration_z', 'g_force',
            'impact_confidence', 'location_lat', 'location_lng', 'speed',
            'triggered_alert', 'is_false_positive', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class CreateMotionDetectionEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = MotionDetectionEvent
        fields = [
            'journey', 'motion_type', 'acceleration_x', 'acceleration_y', 
            'acceleration_z', 'g_force', 'impact_confidence', 'location_lat',
            'location_lng', 'speed'
        ]
    
    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['user'] = request.user
        
        # Auto-trigger alert for crash detection with high confidence
        motion_type = validated_data.get('motion_type')
        confidence = validated_data.get('impact_confidence', 0)
        
        if motion_type == 'crash' and confidence > 0.7:
            validated_data['triggered_alert'] = True
        
        return super().create(validated_data)

class AIFeedbackSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    
    class Meta:
        model = AIFeedback
        fields = [
            'id', 'user', 'user_name', 'feedback_type', 'rating', 'comments',
            'voice_event', 'motion_event', 'chat_session', 'reviewed',
            'review_notes', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class CreateAIFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIFeedback
        fields = [
            'feedback_type', 'rating', 'comments', 'voice_event', 
            'motion_event', 'chat_session'
        ]
    
    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['user'] = request.user
        return super().create(validated_data)

class VoiceTriggerRequestSerializer(serializers.Serializer):
    journey_id = serializers.UUIDField(required=True)
    safe_word = serializers.CharField(required=True)
    confidence = serializers.FloatField(required=True, min_value=0.0, max_value=1.0)
    audio_data = serializers.CharField(required=False, allow_blank=True)  # Base64 encoded audio
    audio_duration = serializers.FloatField(required=False)
    background_noise = serializers.FloatField(required=False)

class MotionTriggerRequestSerializer(serializers.Serializer):
    journey_id = serializers.UUIDField(required=True)
    motion_type = serializers.CharField(required=True)
    acceleration_x = serializers.FloatField(required=True)
    acceleration_y = serializers.FloatField(required=True)
    acceleration_z = serializers.FloatField(required=True)
    g_force = serializers.FloatField(required=False)
    location_lat = serializers.FloatField(required=False)
    location_lng = serializers.FloatField(required=False)
    speed = serializers.FloatField(required=False)