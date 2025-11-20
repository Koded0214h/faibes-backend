from django.contrib import admin
from .models import VoiceDetectionEvent, AIChatSession, AIChatMessage, MotionDetectionEvent, AIFeedback

@admin.register(VoiceDetectionEvent)
class VoiceDetectionEventAdmin(admin.ModelAdmin):
    list_display = ['user', 'safe_word', 'confidence', 'triggered_alert', 'created_at']
    list_filter = ['triggered_alert', 'status', 'created_at']
    search_fields = ['user__full_name', 'safe_word']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Event Information', {
            'fields': ('user', 'journey', 'safe_word', 'confidence')
        }),
        ('Audio Data', {
            'fields': ('audio_duration', 'background_noise_level', 'audio_snippet_url', 'audio_file')
        }),
        ('Processing', {
            'fields': ('processing_time', 'model_version')
        }),
        ('Status & Feedback', {
            'fields': ('status', 'triggered_alert', 'user_feedback', 'feedback_notes')
        }),
    )

@admin.register(AIChatSession)
class AIChatSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'chat_type', 'is_active', 'created_at']
    list_filter = ['chat_type', 'is_active', 'created_at']
    search_fields = ['user__full_name', 'session_token']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(AIChatMessage)
class AIChatMessageAdmin(admin.ModelAdmin):
    list_display = ['session', 'message_type', 'created_at']
    list_filter = ['message_type', 'created_at']
    search_fields = ['session__user__full_name', 'content']
    readonly_fields = ['created_at']

@admin.register(MotionDetectionEvent)
class MotionDetectionEventAdmin(admin.ModelAdmin):
    list_display = ['user', 'motion_type', 'impact_confidence', 'triggered_alert', 'created_at']
    list_filter = ['motion_type', 'triggered_alert', 'created_at']
    search_fields = ['user__full_name']
    readonly_fields = ['created_at']

@admin.register(AIFeedback)
class AIFeedbackAdmin(admin.ModelAdmin):
    list_display = ['user', 'feedback_type', 'rating', 'reviewed', 'created_at']
    list_filter = ['feedback_type', 'rating', 'reviewed', 'created_at']
    search_fields = ['user__full_name', 'comments']
    readonly_fields = ['created_at']