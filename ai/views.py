from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
import logging
from django.utils import timezone

from .models import VoiceDetectionEvent, AIChatSession, AIChatMessage, MotionDetectionEvent, AIFeedback
from .serializers import (
    VoiceDetectionEventSerializer, CreateVoiceDetectionEventSerializer,
    AIChatSessionSerializer, CreateAIChatSessionSerializer,
    AIChatMessageSerializer, ChatMessageSerializer,
    MotionDetectionEventSerializer, CreateMotionDetectionEventSerializer,
    AIFeedbackSerializer, CreateAIFeedbackSerializer,
    VoiceTriggerRequestSerializer, MotionTriggerRequestSerializer
)
from .services import ai_voice_service, ai_motion_service, ai_chat_service, spitch_audio_service
from alerts.services import AlertService
from journey.models import Journey

logger = logging.getLogger(__name__)

@api_view(['POST'])
def trigger_voice_detection(request):
    """Handle voice detection triggers from the frontend"""
    try:
        serializer = VoiceTriggerRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            data = serializer.validated_data
            journey = get_object_or_404(Journey, id=data['journey_id'], user=request.user)
            
            # Process voice trigger
            voice_event, alert = ai_voice_service.process_voice_trigger(
                journey_id=data['journey_id'],
                user=request.user,
                safe_word=data['safe_word'],
                confidence=data['confidence'],
                audio_duration=data.get('audio_duration'),
                background_noise=data.get('background_noise'),
                location_lat=request.data.get('location_lat'),
                location_lng=request.data.get('location_lng'),
                battery_level=request.data.get('battery_level')
            )
            
            response_data = {
                'message': 'Voice detection processed successfully',
                'voice_event': VoiceDetectionEventSerializer(voice_event).data,
                'alert_triggered': alert is not None
            }
            
            if alert:
                response_data['alert'] = {
                    'id': str(alert.id),
                    'type': alert.alert_type,
                    'severity': alert.severity
                }
            
            return Response(response_data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response(
            {'error': f'Voice detection processing failed: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def trigger_motion_detection(request):
    """Handle motion detection triggers from the frontend"""
    try:
        serializer = MotionTriggerRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            data = serializer.validated_data
            journey = get_object_or_404(Journey, id=data['journey_id'], user=request.user)
            
            # Process motion event
            motion_event, alert = ai_motion_service.process_motion_event(
                journey_id=data['journey_id'],
                user=request.user,
                motion_type=data['motion_type'],
                acceleration_data={
                    'x': data['acceleration_x'],
                    'y': data['acceleration_y'],
                    'z': data['acceleration_z']
                },
                g_force=data.get('g_force'),
                location_lat=data.get('location_lat'),
                location_lng=data.get('location_lng'),
                speed=data.get('speed'),
                battery_level=request.data.get('battery_level')
            )
            
            response_data = {
                'message': 'Motion detection processed successfully',
                'motion_event': MotionDetectionEventSerializer(motion_event).data,
                'alert_triggered': alert is not None
            }
            
            if alert:
                response_data['alert'] = {
                    'id': str(alert.id),
                    'type': alert.alert_type,
                    'severity': alert.severity
                }
            
            return Response(response_data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response(
            {'error': f'Motion detection processing failed: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def create_chat_session(request):
    """Create a new AI chat session"""
    try:
        serializer = CreateAIChatSessionSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            session = ai_chat_service.create_chat_session(
                user=request.user,
                journey=serializer.validated_data.get('journey'),
                chat_type=serializer.validated_data.get('chat_type', 'journey_status')
            )
            
            return Response(
                AIChatSessionSerializer(session).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response(
            {'error': f'Chat session creation failed: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def send_chat_message(request, session_id):
    """Send a message in an AI chat session"""
    try:
        session = get_object_or_404(AIChatSession, id=session_id, user=request.user)
        
        serializer = ChatMessageSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        user_message = serializer.validated_data['message']
        
        # Process message and get AI response
        ai_message = ai_chat_service.process_chat_message(session, user_message)
        
        return Response({
            'user_message': user_message,
            'ai_response': AIChatMessageSerializer(ai_message).data,
            'session': AIChatSessionSerializer(session).data
        })
    
    except Exception as e:
        return Response(
            {'error': f'Chat message processing failed: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
def chat_sessions(request):
    """Get user's AI chat sessions"""
    try:
        sessions = AIChatSession.objects.filter(user=request.user).order_by('-created_at')
        serializer = AIChatSessionSerializer(sessions, many=True)
        
        return Response(serializer.data)
    
    except Exception as e:
        return Response(
            {'error': f'Failed to fetch chat sessions: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
def chat_session_detail(request, session_id):
    """Get specific chat session with messages"""
    try:
        session = get_object_or_404(AIChatSession, id=session_id, user=request.user)
        serializer = AIChatSessionSerializer(session)
        
        return Response(serializer.data)
    
    except Exception as e:
        return Response(
            {'error': f'Failed to fetch chat session: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def submit_ai_feedback(request):
    """Submit feedback for AI features"""
    try:
        serializer = CreateAIFeedbackSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            feedback = serializer.save()
            
            return Response(
                AIFeedbackSerializer(feedback).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response(
            {'error': f'Feedback submission failed: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
def voice_detection_history(request):
    """Get user's voice detection history"""
    try:
        voice_events = VoiceDetectionEvent.objects.filter(
            user=request.user
        ).order_by('-created_at')[:50]  # Last 50 events
        
        serializer = VoiceDetectionEventSerializer(voice_events, many=True)
        return Response(serializer.data)
    
    except Exception as e:
        return Response(
            {'error': f'Failed to fetch voice detection history: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
def motion_detection_history(request):
    """Get user's motion detection history"""
    try:
        motion_events = MotionDetectionEvent.objects.filter(
            user=request.user
        ).order_by('-created_at')[:50]  # Last 50 events
        
        serializer = MotionDetectionEventSerializer(motion_events, many=True)
        return Response(serializer.data)
    
    except Exception as e:
        return Response(
            {'error': f'Failed to fetch motion detection history: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def analyze_audio_quality(request):
    """Analyze audio quality (placeholder for advanced analysis)"""
    try:
        audio_data = request.data.get('audio_data')  # Base64 encoded audio
        
        if not audio_data:
            return Response(
                {'error': 'Audio data is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Analyze audio quality
        analysis = ai_voice_service.analyze_audio_quality(audio_data)
        
        return Response({
            'message': 'Audio quality analysis completed',
            'analysis': analysis
        })
    
    except Exception as e:
        return Response(
            {'error': f'Audio analysis failed: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        
        

@api_view(['POST'])
def analyze_audio_emergency(request):
    """Advanced audio analysis for emergency detection"""
    try:
        audio_data = request.data.get('audio_data')
        journey_id = request.data.get('journey_id')
        
        if not audio_data or not journey_id:
            return Response(
                {'error': 'Audio data and journey ID are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        journey = get_object_or_404(Journey, id=journey_id, user=request.user)
        
        # Create user context for analysis
        user_context = {
            'name': request.user.full_name,
            'medical_info': request.user.medical_info,
            'journey_destination': journey.destination_address
        }
        
        # Analyze audio for emergency context
        emergency_detected, analysis_result = ai_voice_service.analyze_audio_for_emergency(
            audio_data, user_context
        )
        
        # Create alert if emergency detected
        alert = None
        if emergency_detected:
            alert = AlertService.create_alert(
                journey=journey,
                alert_type='voice_emergency',
                triggered_by=request.user,
                severity='high',
                trigger_data={
                    'emergency_analysis': analysis_result,
                    'automatic_detection': True
                },
                location_lat=request.data.get('location_lat'),
                location_lng=request.data.get('location_lng')
            )
        
        return Response({
            'emergency_detected': emergency_detected,
            'analysis_result': analysis_result,
            'alert_created': alert is not None,
            'alert_id': str(alert.id) if alert else None
        })
    
    except Exception as e:
        return Response(
            {'error': f'Emergency audio analysis failed: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def process_audio_chunk(request):
    """Process audio chunk for keyword detection (for frontend testing)"""
    try:
        audio_data = request.data.get('audio_data')
        audio_format = request.data.get('audio_format', 'webm')
        target_keywords = request.data.get('keywords', [])
        
        if not audio_data:
            return Response(
                {'error': 'Audio data is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Process audio chunk
        detected_text, confidence, processing_info = spitch_audio_service.process_audio_chunk(
            audio_data, audio_format
        )
        
        # Check for keywords
        keyword_matches = []
        if detected_text and target_keywords:
            detected_lower = detected_text.lower()
            for keyword in target_keywords:
                if keyword.lower() in detected_lower:
                    keyword_matches.append(keyword)
        
        # Analyze audio quality
        quality_analysis = {}
        try:
            quality_analysis = spitch_audio_service.analyze_audio_quality(audio_data)
        except Exception as e:
            logger.error(f"Audio quality analysis failed: {str(e)}")
            quality_analysis = {'error': 'Quality analysis unavailable'}
        
        return Response({
            'detected_text': detected_text,
            'confidence': confidence,
            'keyword_matches': keyword_matches,
            'processing_info': processing_info,
            'quality_analysis': quality_analysis
        })
    
    except Exception as e:
        return Response(
            {'error': f'Audio processing failed: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
def ai_service_status(request):
    """Check status of AI services"""
    try:
        status_info = {
            'gemini_ai': {
                'configured': ai_chat_service.gemini_service.client is not None,
                'status': 'active' if ai_chat_service.gemini_service.client else 'inactive'
            },
            'spitch_audio': {
                'configured': spitch_audio_service.spitch_api_key is not None,
                'status': 'active' if spitch_audio_service.spitch_api_key else 'inactive'
            },
            'voice_detection': {
                'status': 'active',
                'confidence_threshold': 0.7
            },
            'motion_detection': {
                'status': 'active',
                'enhanced_analysis': True
            }
        }
        
        return Response(status_info)
    
    except Exception as e:
        return Response(
            {'error': f'Service status check failed: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )