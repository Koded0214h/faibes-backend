from django.urls import path
from . import views

app_name = 'ai'

urlpatterns = [
    # Voice Detection
    path('voice/trigger/', views.trigger_voice_detection, name='trigger-voice-detection'),
    path('voice/analyze-emergency/', views.analyze_audio_emergency, name='analyze-audio-emergency'),
    path('voice/process-audio/', views.process_audio_chunk, name='process-audio-chunk'),
    path('voice/history/', views.voice_detection_history, name='voice-detection-history'),
    
    # Motion Detection
    path('motion/trigger/', views.trigger_motion_detection, name='trigger-motion-detection'),
    path('motion/history/', views.motion_detection_history, name='motion-detection-history'),
    
    # AI Chatbot
    path('chat/sessions/', views.chat_sessions, name='ai-chat-sessions'),
    path('chat/sessions/create/', views.create_chat_session, name='create-chat-session'),
    path('chat/sessions/<uuid:session_id>/', views.chat_session_detail, name='chat-session-detail'),
    path('chat/sessions/<uuid:session_id>/message/', views.send_chat_message, name='send-chat-message'),
    
    # Feedback
    path('feedback/', views.submit_ai_feedback, name='submit-ai-feedback'),
    
    # Service Status
    path('status/', views.ai_service_status, name='ai-service-status'),
]