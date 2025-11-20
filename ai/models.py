from django.db import models
import uuid
from django.utils import timezone
from django.contrib.auth import get_user_model
from journey.models import Journey

User = get_user_model()

class VoiceDetectionEvent(models.Model):
    """Store voice detection events for analysis and improvement"""
    
    DETECTION_STATUS = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('false_positive', 'False Positive'),
        ('error', 'Error'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Event Information
    journey = models.ForeignKey(Journey, on_delete=models.CASCADE, related_name='voice_events')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='voice_events')
    
    # Detection Data
    safe_word = models.CharField(max_length=50)
    confidence = models.FloatField()  # 0.0 to 1.0
    audio_duration = models.FloatField(null=True, blank=True)  # seconds
    background_noise_level = models.FloatField(null=True, blank=True)  # 0.0 to 1.0
    
    # Audio Storage
    audio_snippet_url = models.URLField(blank=True)  # URL to stored audio file
    audio_file = models.FileField(upload_to='voice_detection/', null=True, blank=True)
    
    # Processing Information
    processing_time = models.FloatField(null=True, blank=True)  # milliseconds
    model_version = models.CharField(max_length=50, default='v1.0')
    
    # Status
    status = models.CharField(max_length=20, choices=DETECTION_STATUS, default='pending')
    triggered_alert = models.BooleanField(default=False)
    
    # Feedback
    user_feedback = models.BooleanField(null=True, blank=True)  # True if correct detection
    feedback_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'voice_detection_events'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.full_name} - {self.safe_word} ({self.confidence:.2f})"

class AIChatSession(models.Model):
    """AI chatbot sessions for safety network members"""
    
    CHAT_TYPES = [
        ('journey_status', 'Journey Status'),
        ('emergency_info', 'Emergency Information'),
        ('general_help', 'General Help'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Session Information
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_sessions')
    journey = models.ForeignKey(Journey, on_delete=models.CASCADE, null=True, blank=True, related_name='ai_sessions')
    chat_type = models.CharField(max_length=20, choices=CHAT_TYPES, default='journey_status')
    
    # Session Management
    session_token = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    
    # Context
    context_data = models.JSONField(default=dict, blank=True)  # Additional context for the AI
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'ai_chat_sessions'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.full_name} - {self.chat_type} - {self.created_at}"

class AIChatMessage(models.Model):
    """Individual messages in AI chat sessions"""
    
    MESSAGE_TYPES = [
        ('user', 'User Message'),
        ('assistant', 'AI Response'),
        ('system', 'System Message'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(AIChatSession, on_delete=models.CASCADE, related_name='messages')
    
    # Message Content
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES)
    content = models.TextField()
    
    # AI Processing
    ai_model = models.CharField(max_length=50, blank=True)
    processing_time = models.FloatField(null=True, blank=True)  # milliseconds
    tokens_used = models.IntegerField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_chat_messages'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.session.user.full_name} - {self.message_type} - {self.content[:50]}"

class MotionDetectionEvent(models.Model):
    """Store motion and impact detection events"""
    
    MOTION_TYPES = [
        ('crash', 'Crash/Impact'),
        ('sudden_stop', 'Sudden Stop'),
        ('hard_braking', 'Hard Braking'),
        ('sharp_turn', 'Sharp Turn'),
        ('excessive_speed', 'Excessive Speed'),
        ('no_movement', 'No Movement'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Event Information
    journey = models.ForeignKey(Journey, on_delete=models.CASCADE, related_name='motion_events')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='motion_events')
    
    # Motion Data
    motion_type = models.CharField(max_length=20, choices=MOTION_TYPES)
    acceleration_x = models.FloatField()
    acceleration_y = models.FloatField()
    acceleration_z = models.FloatField()
    
    # Impact Metrics
    g_force = models.FloatField(null=True, blank=True)
    impact_confidence = models.FloatField()  # 0.0 to 1.0
    
    # Location Context
    location_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    speed = models.FloatField(null=True, blank=True)  # km/h
    
    # Status
    triggered_alert = models.BooleanField(default=False)
    is_false_positive = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'motion_detection_events'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.full_name} - {self.motion_type} - {self.g_force or 0:.2f}g"

class AIFeedback(models.Model):
    """Store user feedback for AI improvements"""
    
    FEEDBACK_TYPES = [
        ('voice_detection', 'Voice Detection'),
        ('motion_detection', 'Motion Detection'),
        ('chatbot_response', 'Chatbot Response'),
        ('alert_accuracy', 'Alert Accuracy'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_feedback')
    
    # Feedback Information
    feedback_type = models.CharField(max_length=20, choices=FEEDBACK_TYPES)
    rating = models.IntegerField()  # 1-5 scale
    comments = models.TextField(blank=True)
    
    # Related Events
    voice_event = models.ForeignKey(VoiceDetectionEvent, on_delete=models.SET_NULL, null=True, blank=True)
    motion_event = models.ForeignKey(MotionDetectionEvent, on_delete=models.SET_NULL, null=True, blank=True)
    chat_session = models.ForeignKey(AIChatSession, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Resolution
    reviewed = models.BooleanField(default=False)
    review_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_feedback'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.full_name} - {self.feedback_type} - {self.rating}/5"