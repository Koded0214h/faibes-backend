import logging
import json
import base64
import io
import tempfile
import requests
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from django.core.files.base import ContentFile

# --- Spitch/Audio Libraries ---
# REMOVED: speech_recognition, pydub, librosa, numpy (using Spitch API instead)

# AI Libraries - Updated to google-genai
import google.genai as genai
from google.genai.types import GenerationConfig # Explicitly import GenerationConfig
import numpy as np # Retained for AIMotionService G-force calculation only

from .models import VoiceDetectionEvent, MotionDetectionEvent, AIChatSession, AIChatMessage
from alerts.services import AlertService
from alerts.models import Alert
from journey.models import Journey
from utils.notifications import send_emergency_alert

logger = logging.getLogger(__name__)

class SpitchAudioService:
    """Spitch-based audio processing service for voice detection"""
    
    def __init__(self):
        # Removed self.recognizer = sr.Recognizer()
        self.configure_spitch()
    
    def configure_spitch(self):
        """Configure Spitch audio processing"""
        # Spitch configuration - you would add your Spitch API credentials here
        self.spitch_api_key = getattr(settings, 'SPITCH_API_KEY', None)
        # Using a single base URL for all Spitch operations
        self.spitch_base_url = getattr(settings, 'SPITCH_BASE_URL', 'https://api.spitch.ai/v1') 
        
        if self.spitch_api_key:
            logger.info("Spitch audio service configured successfully")
        else:
            # We must fail if the key is missing, as there is no fallback now
            logger.error("Spitch API key not found. SpitchAudioService is disabled.")
    
    def _prepare_spitch_request(self, audio_data, endpoint, audio_format='wav'):
        """Helper to prepare files and headers for Spitch API calls."""
        if not self.spitch_api_key:
            raise ConnectionError("Spitch API key is missing.")

        # Handle base64 encoded audio (assuming input is pre-decoded bytes or a base64 string)
        if isinstance(audio_data, str):
             # Extract base64 data if it is a data URL
            if audio_data.startswith('data:audio'):
                audio_data = audio_data.split(',')[1]
            audio_data = base64.b64decode(audio_data)

        audio_file = io.BytesIO(audio_data)
        
        files = {'audio': (f'audio.{audio_format}', audio_file, f'audio/{audio_format}')}
        headers = {'Authorization': f'Bearer {self.spitch_api_key}'}
        
        return files, headers, f"{self.spitch_base_url}/{endpoint}"

    def process_audio_chunk(self, audio_data, audio_format='webm', sample_rate=16000):
        """
        Process audio chunk using Spitch for STT/keyword detection
        This now ONLY uses the Spitch API (ASR/STT endpoint).
        Returns: (detected_text: str, confidence: float, processing_data: dict)
        """
        if not self.spitch_api_key:
            return "", 0.0, {"error": "Spitch API not configured."}
            
        try:
            # Spitch API should handle format conversion internally, so we send the raw data
            files, headers, url = self._prepare_spitch_request(
                audio_data, 
                'asr/transcribe', # Using ASR/transcribe endpoint for general STT
                audio_format=audio_format
            )
            
            # Add parameters for STT (e.g., sample rate, language)
            data = {
                'sample_rate': sample_rate, 
                'language': 'en', # Assuming English for this context
            }
            
            response = requests.post(
                url,
                files=files,
                headers=headers,
                data=data,
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                detected_text = result.get('text', '')
                # Spitch usually provides the confidence score for the entire utterance or per word
                confidence = result.get('confidence', 0.0) 
                
                return detected_text, confidence, {
                    'spitch_processing': True,
                    'model_version': result.get('model_version', 'spitch_asr'),
                    'processing_time': result.get('processing_time_ms', 0)
                }
            else:
                logger.error(f"Spitch ASR API failed: {response.status_code} - {response.text}")
                return "", 0.0, {"error": f"Spitch API failed: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Spitch ASR processing failed: {str(e)}")
            return "", 0.0, {"error": str(e)}
    
    # --- Format Conversion and Quality Analysis using Spitch API ---
    
    def convert_to_wav(self, audio_data, original_format, target_sample_rate=16000):
        """
        Delegates audio conversion to Spitch's utility API/service.
        Returns: bytes of WAV audio
        """
        if not self.spitch_api_key:
            raise ConnectionError("Spitch API not configured for conversion.")
        
        try:
            # Assuming a Spitch utility endpoint exists for format conversion
            files, headers, url = self._prepare_spitch_request(
                audio_data, 
                'utils/convert', # Mocked conversion endpoint
                audio_format=original_format
            )
            
            data = {'target_format': 'wav', 'sample_rate': target_sample_rate}
            
            response = requests.post(
                url, files=files, headers=headers, data=data, timeout=10
            )
            
            if response.status_code == 200 and response.content:
                # Assuming the API returns the raw converted audio bytes
                return response.content
            else:
                raise ValueError(f"Spitch conversion failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Spitch Audio conversion failed: {str(e)}")
            raise

    def analyze_audio_quality(self, audio_data):
        """
        Delegates audio quality analysis to a specialized Spitch API endpoint.
        Returns: dict of audio metrics
        """
        if not self.spitch_api_key:
            raise ConnectionError("Spitch API not configured for quality analysis.")
            
        try:
            # Assuming a Spitch endpoint for Voice Activity Detection (VAD) and Quality
            files, headers, url = self._prepare_spitch_request(
                audio_data, 
                'vad/quality-analysis', # Mocked analysis endpoint
                audio_format='wav' # Assuming we send pre-converted WAV for analysis
            )
            
            response = requests.post(
                url, files=files, headers=headers, timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                # Spitch should return standardized metrics
                return {
                    'duration': result.get('duration_sec', 0.0),
                    'rms_energy': result.get('rms_energy', 0.0),
                    'background_noise_level': result.get('noise_level', 0.0),
                    'voice_activity': result.get('voice_activity_detected', False),
                    'recommendation': result.get('quality_recommendation', 'Good quality')
                }
            else:
                logger.error(f"Spitch Quality Analysis failed: {response.status_code}")
                return { 'voice_activity': False, 'recommendation': 'Analysis failed' }
                
        except Exception as e:
            logger.error(f"Spitch quality analysis failed: {str(e)}")
            return { 'voice_activity': False, 'recommendation': 'Analysis failed due to error' }
    
    def detect_safe_word(self, audio_data, user_safe_word, audio_format='webm'):
        """
        Detect safe word in audio data using Spitch's specific keyword/phrase detection model.
        Returns: (detected: bool, confidence: float, processing_info: dict)
        """
        if not self.spitch_api_key:
            return False, 0.0, {"error": "Spitch API not configured."}
            
        try:
            # Use Spitch's advanced keyword detection model/endpoint
            files, headers, url = self._prepare_spitch_request(
                audio_data, 
                'asr/keyword-spotting', # Mocked keyword detection endpoint
                audio_format=audio_format
            )
            
            # Pass the target keyword/phrase to the API
            data = {'keyword': user_safe_word, 'language': 'en'}
            
            response = requests.post(
                url, files=files, headers=headers, data=data, timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                safe_word_detected = result.get('keyword_detected', False)
                confidence = result.get('confidence', 0.0) 
                detected_text = result.get('full_transcription', '')
                
                processing_info = {
                    'spitch_processing': True,
                    'model_version': result.get('model_version', 'spitch_keyword'),
                    'detected_text': detected_text,
                    'safe_word_expected': user_safe_word,
                    'safe_word_detected': safe_word_detected
                }
                
                return safe_word_detected, confidence, processing_info
            else:
                logger.error(f"Spitch Safe Word API failed: {response.status_code} - {response.text}")
                return False, 0.0, {"error": f"Spitch API failed: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Safe word detection failed: {str(e)}")
            return False, 0.0, {"error": str(e)}

# --- Remaining classes are unchanged in functionality but now rely purely on SpitchAudioService ---

class GeminiAIService:
    """Google Gemini AI service for advanced processing (using google-genai)"""
    
    def __init__(self):
        self.client = None
        self.model_name = 'gemini-pro' # Use gemini-pro for text tasks
        self.configure_gemini()
    
    def configure_gemini(self):
        """Configure Google Gemini AI using google-genai.Client"""
        try:
            api_key = getattr(settings, 'GOOGLE_AI_API_KEY', None)
            if api_key:
                # Initialize the Client explicitly with the API key
                self.client = genai.Client(api_key=api_key)
                logger.info("Google Gemini AI configured successfully with genai.Client")
            else:
                logger.warning("Google AI API key not found")
                self.client = None
        except Exception as e:
            logger.error(f"Failed to configure Gemini AI: {str(e)}")
            self.client = None
    
    def generate_chat_response(self, prompt, context=None, temperature=0.7):
        """Generate response using Gemini AI"""
        if not self.client:
            return self._fallback_response(prompt, context)
        
        try:
            # Build enhanced prompt with context
            enhanced_prompt = self._build_enhanced_prompt(prompt, context)
            
            # Define generation configuration
            config = GenerationConfig(
                temperature=temperature,
                top_p=0.8,
                top_k=40,
                max_output_tokens=1024,
            )
            
            # Generate response using the client and model name
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=enhanced_prompt,
                config=config,
            )
            
            return response.text, {
                'model_used': self.model_name,
                'tokens_estimated': len(response.text.split()),
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Gemini AI response failed: {str(e)}")
            fallback_response = self._fallback_response(prompt, context)
            return fallback_response, {
                'model_used': 'fallback',
                'error': str(e),
                'success': False
            }
    
    def analyze_emergency_context(self, user_data, journey_data, location_data):
        """Use Gemini to analyze emergency context and provide insights"""
        if not self.client:
            return self._fallback_emergency_analysis()
        
        try:
            prompt = f"""
            Analyze this emergency situation and provide safety recommendations:
            
            User: {user_data.get('full_name', 'Unknown')}
            Medical Info: {user_data.get('medical_info', {})}
            Current Journey: {journey_data.get('destination', 'Unknown')}
            Journey Status: {journey_data.get('status', 'Unknown')}
            Location: {location_data}
            
            This is a potential emergency situation detected by the FAIBES safety system.
            Please provide:
            1. Immediate safety recommendations
            2. Questions to ask when contacting the user
            3. Emergency contact guidance
            4. Local emergency service considerations (if location is known)
            
            Keep response concise and actionable.
            """
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return response.text, {'analysis_complete': True}
            
        except Exception as e:
            logger.error(f"Emergency context analysis failed: {str(e)}")
            return self._fallback_emergency_analysis(), {'analysis_complete': False}
    
    def _build_enhanced_prompt(self, prompt, context):
        """Build enhanced prompt with context for Gemini"""
        base_context = """
        You are FAIBES Assistant, an AI safety assistant for the Family AI-Based Emergency Safety System.
        Your role is to provide helpful, accurate, and safety-focused information.
        
        Key guidelines:
        - Always prioritize safety and emergency procedures
        - Be concise and actionable
        - For journey status, provide clear location-based information
        - For emergencies, provide immediate action steps
        - Never provide medical advice beyond basic first aid guidance
        - Direct users to contact emergency services for real emergencies
        
        """
        
        if context:
            context_str = json.dumps(context, indent=2)
            return f"{base_context}\nContext: {context_str}\n\nUser Query: {prompt}\n\nResponse:"
        else:
            return f"{base_context}\nUser Query: {prompt}\n\nResponse:"
    
    def _fallback_response(self, prompt, context):
        """Provide fallback response when Gemini is unavailable"""
        prompt_lower = prompt.lower()
        
        if any(word in prompt_lower for word in ['emergency', 'help', 'panic', 'accident']):
            return "I'm currently experiencing technical difficulties. For emergencies, please trigger the panic button in the FAIBES app immediately and contact local emergency services."
        
        elif any(word in prompt_lower for word in ['where', 'location', 'status']):
            return "I'm unable to access journey information at the moment. Please check the FAIBES app for real-time location updates and journey status."
        
        else:
            return "I'm currently unavailable. Please try again shortly or use the FAIBES app for safety features and journey tracking."
    
    def _fallback_emergency_analysis(self):
        """Fallback emergency analysis"""
        return """
        Immediate Safety Recommendations:
        1. Attempt to contact the user directly via phone call
        2. Check the FAIBES app for real-time location
        3. If no response, contact local emergency services
        4. Notify other safety network members
        
        Emergency Contact Guidance:
        - Provide emergency services with the user's medical information
        - Share the last known location from FAIBES
        - Stay on the line until help arrives
        
        Note: Advanced analysis unavailable. Follow standard emergency procedures.
        """

class AIVoiceService:
    """Enhanced voice detection service with Spitch integration"""
    
    def __init__(self):
        self.audio_service = SpitchAudioService()
        self.gemini_service = GeminiAIService()
    
    def process_voice_trigger(self, journey_id, user, safe_word, audio_data=None, **kwargs):
        """
        Process voice trigger with real audio processing
        Returns: (voice_event: VoiceDetectionEvent, alert: Alert or None)
        """
        try:
            journey = Journey.objects.get(id=journey_id, user=user)
            
            confidence = kwargs.get('confidence', 0.0)
            processing_info = {}
            
            # Process audio if provided
            if audio_data:
                # 1. Detect safe word using Spitch
                safe_word_detected, processed_confidence, processing_info = self.audio_service.detect_safe_word(
                    audio_data, safe_word, kwargs.get('audio_format', 'webm')
                )
                
                # Use processed confidence
                if processed_confidence > 0:
                    confidence = processed_confidence
                
                # 2. Analyze audio quality using Spitch
                try:
                    # Note: We assume Spitch can take the raw audio for quality analysis
                    quality_analysis = self.audio_service.analyze_audio_quality(audio_data)
                    processing_info['quality_analysis'] = quality_analysis
                except Exception as e:
                    logger.warning(f"Spitch Quality analysis failed: {e}")
                
            # Create voice detection event
            voice_event = VoiceDetectionEvent.objects.create(
                journey=journey,
                user=user,
                safe_word=safe_word,
                confidence=confidence,
                audio_duration=kwargs.get('audio_duration'),
                # Access Spitch analysis results
                background_noise_level=processing_info.get('quality_analysis', {}).get('background_noise_level'),
                audio_snippet_url=kwargs.get('audio_snippet_url', ''),
                processing_time=processing_info.get('processing_time', kwargs.get('processing_time')),
                model_version=processing_info.get('model_version', 'spitch_keyword'),
                triggered_alert=confidence > 0.7,  # 70% confidence threshold for alerts
                status='confirmed' if confidence > 0.8 else 'pending'
            )
            
            # Store processing info as trigger data
            processing_info['audio_processed'] = audio_data is not None
            
            alert = None
            if voice_event.triggered_alert:
                # Create emergency alert
                alert = AlertService.create_alert(
                    journey=journey,
                    alert_type='voice_trigger',
                    triggered_by=user,
                    severity='high',
                    trigger_data={
                        'safe_word': safe_word,
                        'confidence': confidence,
                        'voice_event_id': str(voice_event.id),
                        'audio_processing': processing_info,
                        'automatic_detection': audio_data is not None
                    },
                    location_lat=kwargs.get('location_lat'),
                    location_lng=kwargs.get('location_lng'),
                    battery_level=kwargs.get('battery_level')
                )
                
                logger.info(f"Voice trigger alert created: {alert.id}")
            
            return voice_event, alert
            
        except Journey.DoesNotExist:
            logger.error(f"Journey not found: {journey_id}")
            raise
        except Exception as e:
            logger.error(f"Voice trigger processing failed: {str(e)}")
            raise
    
    def analyze_audio_for_emergency(self, audio_data, user_context):
        """
        Advanced audio analysis for emergency context detection (using Spitch for STT and VAD)
        Returns: (emergency_detected: bool, analysis_result: dict)
        """
        try:
            # 1. Analyze audio quality/VAD using Spitch
            quality_analysis = self.audio_service.analyze_audio_quality(audio_data)
            
            # 2. Use Spitch for STT if voice activity is detected
            if quality_analysis.get('voice_activity'):
                detected_text, confidence, _ = self.audio_service.process_audio_chunk(
                    audio_data, 
                    audio_format='webm' # Assuming input format
                )
                
                if detected_text and confidence > 0.5:
                    # 3. Use Gemini to analyze the transcribed text for emergency cues
                    analysis_prompt = f"""
                    Analyze this detected speech for emergency cues: "{detected_text}"
                    
                    User Context: {user_context}
                    
                    Is this likely an emergency situation? Look for:
                    - Distress words (help, emergency, accident, etc.)
                    - Urgent tone indicators
                    - Contextual emergency signals
                    
                    Respond with ONLY: EMERGENCY or NOT_EMERGENCY
                    """
                    
                    gemini_response, _ = self.gemini_service.generate_chat_response(analysis_prompt)
                    
                    emergency_detected = "EMERGENCY" in gemini_response.upper()
                    
                    return emergency_detected, {
                        'detected_text': detected_text,
                        'confidence': confidence,
                        'gemini_analysis': gemini_response,
                        'quality_analysis': quality_analysis
                    }
                
            return False, {
                'voice_activity': quality_analysis.get('voice_activity', False),
                'quality_analysis': quality_analysis,
                'reason': 'No speech detected or low confidence'
            }
            
        except Exception as e:
            logger.error(f"Emergency audio analysis failed: {str(e)}")
            return False, {'error': str(e)}

class AIChatService:
    """Enhanced chat service with Gemini AI"""
    
    def __init__(self):
        self.gemini_service = GeminiAIService()
    
    def create_chat_session(self, user, journey=None, chat_type='journey_status'):
        """Create a new AI chat session"""
        session = AIChatSession.objects.create(
            user=user,
            journey=journey,
            chat_type=chat_type,
            session_token=self.generate_session_token()
        )
        
        # Add welcome message using Gemini
        welcome_prompt = self._create_welcome_prompt(chat_type, user, journey)
        welcome_message, _ = self.gemini_service.generate_chat_response(welcome_prompt)
        
        AIChatMessage.objects.create(
            session=session,
            message_type='assistant',
            content=welcome_message,
            ai_model='gemini-pro'
        )
        
        return session
    
    def process_chat_message(self, session, user_message):
        """Process user message and generate AI response using Gemini"""
        start_time = timezone.now()
        
        try:
            # Get conversation history
            previous_messages = session.messages.order_by('created_at')[:10]
            
            # Create context for the AI
            context = self.create_chat_context(session, previous_messages)
            
            # Generate response using Gemini
            ai_response, processing_info = self.gemini_service.generate_chat_response(
                user_message, 
                context
            )
            
            # Save user message
            user_msg = AIChatMessage.objects.create(
                session=session,
                message_type='user',
                content=user_message
            )
            
            # Save AI response
            processing_time = (timezone.now() - start_time).total_seconds() * 1000
            ai_msg = AIChatMessage.objects.create(
                session=session,
                message_type='assistant',
                content=ai_response,
                ai_model=processing_info.get('model_used', 'unknown'),
                processing_time=processing_time,
                tokens_used=processing_info.get('tokens_estimated', 0)
            )
            
            # Update session
            session.updated_at = timezone.now()
            session.save()
            
            return ai_msg
            
        except Exception as e:
            logger.error(f"Chat message processing failed: {str(e)}")
            
            # Create error response
            error_msg = AIChatMessage.objects.create(
                session=session,
                message_type='assistant',
                content="I apologize, but I'm having trouble processing your request. Please try again or contact support if the issue persists.",
                ai_model='error',
                processing_time=(timezone.now() - start_time).total_seconds() * 1000
            )
            
            return error_msg
    
    def create_chat_context(self, session, previous_messages):
        """Create enhanced context for AI chat"""
        context = {
            'user': {
                'name': session.user.full_name,
                'phone': session.user.phone,
                'medical_info': session.user.medical_info
            },
            'chat_type': session.chat_type,
            'timestamp': timezone.now().isoformat(),
            'conversation_history': []
        }
        
        # Add conversation history
        for msg in previous_messages:
            context['conversation_history'].append({
                'role': 'user' if msg.message_type == 'user' else 'assistant',
                'content': msg.content,
                'timestamp': msg.created_at.isoformat()
            })
        
        if session.journey:
            context['journey'] = {
                'id': str(session.journey.id),
                'destination': session.journey.destination_address,
                'status': session.journey.status,
                'started_at': session.journey.actual_start.isoformat() if session.journey.actual_start else None,
                'estimated_arrival': session.journey.estimated_arrival.isoformat() if session.journey.estimated_arrival else None
            }
            
            # Add latest location and route information
            latest_location = session.journey.locations.order_by('-timestamp').first()
            if latest_location:
                context['journey']['current_location'] = {
                    'lat': float(latest_location.latitude),
                    'lng': float(latest_location.longitude),
                    'speed': latest_location.speed,
                    'timestamp': latest_location.timestamp.isoformat()
                }
        
        # Add safety network info for emergency chats
        if session.chat_type == 'emergency_info':
            context['safety_network'] = session.user.safety_network
            context['emergency_contacts'] = [
                {'name': contact.name, 'phone': contact.phone}
                for contact in session.user.emergency_contacts.filter(is_active=True)
            ]
        
        return context
    
    def _create_welcome_prompt(self, chat_type, user, journey):
        """Create welcome prompt for Gemini"""
        base_prompt = f"Create a welcome message for {user.full_name} "
        
        if chat_type == 'journey_status':
            if journey:
                return base_prompt + f"who is on a journey to {journey.destination_address}. Introduce yourself as FAIBES Assistant and explain you can help with journey status and safety information."
            else:
                return base_prompt + ". Introduce yourself as FAIBES Assistant and explain you can help with journey status and safety information."
        
        elif chat_type == 'emergency_info':
            return base_prompt + ". Introduce yourself as FAIBES Assistant for emergency information and safety procedures. Be reassuring but direct."
        
        else:
            return base_prompt + ". Introduce yourself as FAIBES Assistant and offer help with general questions about the safety system."
    
    def generate_session_token(self):
        """Generate unique session token"""
        import secrets
        return secrets.token_urlsafe(32)

# ... [keep all your existing imports and classes]

class AIMotionService:
    """Enhanced motion detection with AI analysis"""
    
    def __init__(self):
        self.gemini_service = GeminiAIService()  # FIXED: Initialize here
    
    def calculate_g_force(self, acceleration_data):
        """Calculate G-force from acceleration data (Magnitude / g)."""
        # Earth gravity is approximately 9.8 m/s²
        
        # Calculate magnitude of acceleration vector
        accel_magnitude = (
            acceleration_data['x']**2 + 
            acceleration_data['y']**2 + 
            acceleration_data['z']**2
        ) ** 0.5
        
        return accel_magnitude / 9.8
    
    def calculate_enhanced_impact_confidence(self, acceleration_data, motion_type, speed):
        """Enhanced impact confidence calculation based on G-force and speed."""
        
        # Calculate magnitude of acceleration vector
        accel_magnitude = (
            acceleration_data['x']**2 + 
            acceleration_data['y']**2 + 
            acceleration_data['z']**2
        ) ** 0.5
        
        # Adjust confidence based on motion type and speed
        base_confidence = 0.0
        
        if motion_type == 'crash':
            # High G-force indicates potential crash
            if accel_magnitude > 4.0:  # 4G threshold
                base_confidence = min(1.0, (accel_magnitude - 4.0) / 3.0)
            else:
                base_confidence = max(0.0, accel_magnitude / 4.0)
            
            # Adjust for speed (higher speed = higher confidence)
            speed_factor = min(1.0, speed / 80.0)  # Normalize to 80 km/h
            base_confidence = min(1.0, base_confidence * (1 + speed_factor * 0.5))
        
        elif motion_type == 'sudden_stop':
            # Sudden deceleration in forward direction (X-axis)
            decel_confidence = min(1.0, abs(acceleration_data['x']) / 5.0)
            base_confidence = decel_confidence
        
        elif motion_type == 'hard_braking':
            base_confidence = min(1.0, abs(acceleration_data['x']) / 4.0)
        
        elif motion_type == 'sharp_turn':
            # Lateral acceleration (Y-axis)
            lateral_confidence = min(1.0, (abs(acceleration_data['y']) - 2.0) / 3.0)
            base_confidence = max(0.0, lateral_confidence)
        
        return base_confidence
    
    def should_trigger_enhanced_alert(self, motion_type, confidence, context):
        """Enhanced alert triggering logic with contextual adjustment."""
        alert_thresholds = {
            'crash': 0.7,
            'sudden_stop': 0.8,
            'hard_braking': 0.8,
            'sharp_turn': 0.85,
            'excessive_speed': 0.9,
            'no_movement': 0.95,
        }
        
        threshold = alert_thresholds.get(motion_type, 1.0)
        
        # Adjust threshold based on context
        speed = context.get('speed', 0)
        if motion_type == 'crash' and speed > 50:  # Higher speed = lower threshold
            threshold *= 0.8
        
        return confidence >= threshold
    
    def analyze_motion_emergency_context(self, user, journey, motion_event, context):
        """Use Gemini to analyze motion emergency context"""
        try:
            # Prepare context data for the Gemini service call
            user_data = {
                'full_name': user.full_name,
                'medical_info': user.medical_info
            }
            
            journey_data = {
                'destination': journey.destination_address,
                'status': journey.status
            }
            
            # Format location data as a string for the external service call
            location_data = f"Lat: {context.get('location_lat')}, Lng: {context.get('location_lng')}"
            
            analysis, _ = self.gemini_service.analyze_emergency_context( 
                user_data, journey_data, location_data
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Motion emergency analysis failed: {str(e)}")
            return "Emergency analysis unavailable."
    
    def process_motion_event(self, journey_id, user, motion_type, acceleration_data, **kwargs):
        """
        Process motion detection event with enhanced AI analysis and alert creation.
        """
        try:
            journey = Journey.objects.get(id=journey_id, user=user)
            
            # Calculate impact confidence with enhanced algorithm
            impact_confidence = self.calculate_enhanced_impact_confidence(
                acceleration_data, motion_type, kwargs.get('speed', 0)
            )
            
            # Calculate g_force
            g_force = self.calculate_g_force(acceleration_data)
            
            triggered_alert = self.should_trigger_enhanced_alert(motion_type, impact_confidence, kwargs)
            
            # Create motion detection event
            motion_event = MotionDetectionEvent.objects.create(
                journey=journey,
                user=user,
                motion_type=motion_type,
                acceleration_x=acceleration_data['x'],
                acceleration_y=acceleration_data['y'],
                acceleration_z=acceleration_data['z'],
                g_force=g_force,
                impact_confidence=impact_confidence,
                location_lat=kwargs.get('location_lat'),
                location_lng=kwargs.get('location_lng'),
                speed=kwargs.get('speed'),
                triggered_alert=triggered_alert
            )
            
            alert = None
            emergency_analysis = ""
            if motion_event.triggered_alert:
                # Use Gemini to analyze emergency context for severe events
                if impact_confidence > 0.8:
                    emergency_analysis = self.analyze_motion_emergency_context(
                        user, journey, motion_event, kwargs
                    )
                
                # Create Alert
                alert = AlertService.create_alert(
                    journey=journey,
                    alert_type='motion_crash' if motion_type == 'crash' else 'motion_anomaly',
                    triggered_by=user,
                    severity='critical' if motion_type == 'crash' and impact_confidence > 0.8 else 'high',
                    trigger_data={
                        'motion_type': motion_type,
                        'impact_confidence': impact_confidence,
                        'g_force': motion_event.g_force,
                        'speed': kwargs.get('speed'),
                        'motion_event_id': str(motion_event.id),
                        'emergency_analysis': emergency_analysis
                    },
                    location_lat=kwargs.get('location_lat'),
                    location_lng=kwargs.get('location_lng'),
                    battery_level=kwargs.get('battery_level')
                )
                
                logger.info(f"Motion detection alert created: {alert.id}")
            
            return motion_event, alert
            
        except Exception as e:
            logger.error(f"Motion event processing failed: {str(e)}")
            raise

# Global service instances 
spitch_audio_service = SpitchAudioService()
gemini_ai_service = GeminiAIService()
ai_voice_service = AIVoiceService()
ai_motion_service = AIMotionService()
ai_chat_service = AIChatService()