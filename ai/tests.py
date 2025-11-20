import json
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch, MagicMock
from decimal import Decimal

from .models import VoiceDetectionEvent, AIChatSession, AIChatMessage, MotionDetectionEvent, AIFeedback
from journey.models import Journey

User = get_user_model()

class VoiceDetectionEventModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone='+1234567890',
            email='test@example.com',
            password='testpass123',
            full_name='Test User'
        )
        self.journey = Journey.objects.create(
            user=self.user,
            start_address='Start Address',
            destination_address='Destination Address'
        )

    def test_voice_detection_event_creation(self):
        event = VoiceDetectionEvent.objects.create(
            journey=self.journey,
            user=self.user,
            safe_word='help',
            confidence=0.85,
            status='confirmed'
        )
        self.assertEqual(event.safe_word, 'help')
        self.assertEqual(event.confidence, 0.85)
        self.assertEqual(event.status, 'confirmed')
        self.assertEqual(str(event), f"{self.user.full_name} - help (0.85)")

    def test_voice_detection_event_str(self):
        event = VoiceDetectionEvent.objects.create(
            journey=self.journey,
            user=self.user,
            safe_word='test',
            confidence=0.75
        )
        expected = f"{self.user.full_name} - test (0.750)"
        self.assertEqual(str(event), expected)

class AIChatSessionModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone='+1234567890',
            email='test@example.com',
            password='testpass123',
            full_name='Test User'
        )

    def test_ai_chat_session_creation(self):
        session = AIChatSession.objects.create(
            user=self.user,
            chat_type='journey_status',
            session_token='test_token_123'
        )
        self.assertEqual(session.chat_type, 'journey_status')
        self.assertEqual(session.is_active, True)
        self.assertEqual(str(session), f"{self.user.full_name} - journey_status - {session.created_at}")

class AIChatMessageModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone='+1234567890',
            email='test@example.com',
            password='testpass123',
            full_name='Test User'
        )
        self.session = AIChatSession.objects.create(
            user=self.user,
            chat_type='general_help'
        )

    def test_ai_chat_message_creation(self):
        message = AIChatMessage.objects.create(
            session=self.session,
            message_type='user',
            content='Hello AI'
        )
        self.assertEqual(message.message_type, 'user')
        self.assertEqual(message.content, 'Hello AI')
        self.assertEqual(str(message), f"{self.user.full_name} - user - Hello AI")

class MotionDetectionEventModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone='+1234567890',
            email='test@example.com',
            password='testpass123',
            full_name='Test User'
        )
        self.journey = Journey.objects.create(
            user=self.user,
            start_address='Start',
            destination_address='End'
        )

    def test_motion_detection_event_creation(self):
        event = MotionDetectionEvent.objects.create(
            journey=self.journey,
            user=self.user,
            motion_type='crash',
            acceleration_x=5.0,
            acceleration_y=2.0,
            acceleration_z=1.0,
            impact_confidence=0.9
        )
        self.assertEqual(event.motion_type, 'crash')
        self.assertEqual(event.acceleration_x, 5.0)
        self.assertEqual(str(event), f"{self.user.full_name} - crash - 0.00g")

class AIFeedbackModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone='+1234567890',
            email='test@example.com',
            password='testpass123',
            full_name='Test User'
        )

    def test_ai_feedback_creation(self):
        feedback = AIFeedback.objects.create(
            user=self.user,
            feedback_type='voice_detection',
            rating=4,
            comments='Good detection'
        )
        self.assertEqual(feedback.rating, 4)
        self.assertEqual(feedback.comments, 'Good detection')
        self.assertEqual(str(feedback), f"{self.user.full_name} - voice_detection - 4/5")

class AISerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone='+1234567890',
            email='test@example.com',
            password='testpass123',
            full_name='Test User'
        )
        self.journey = Journey.objects.create(
            user=self.user,
            start_address='Start',
            destination_address='End'
        )

    def test_voice_detection_event_serializer(self):
        from .serializers import VoiceDetectionEventSerializer
        event = VoiceDetectionEvent.objects.create(
            journey=self.journey,
            user=self.user,
            safe_word='help',
            confidence=0.8
        )
        serializer = VoiceDetectionEventSerializer(event)
        data = serializer.data
        self.assertIn('safe_word', data)
        self.assertEqual(data['safe_word'], 'help')

    def test_create_voice_detection_event_serializer(self):
        from .serializers import CreateVoiceDetectionEventSerializer
        data = {
            'journey': self.journey.id,
            'safe_word': 'test',
            'confidence': 0.9
        }
        serializer = CreateVoiceDetectionEventSerializer(data=data, context={'request': MagicMock(user=self.user)})
        self.assertTrue(serializer.is_valid())

    def test_motion_trigger_request_serializer(self):
        from .serializers import MotionTriggerRequestSerializer
        data = {
            'journey_id': str(self.journey.id),
            'motion_type': 'crash',
            'acceleration_x': 5.0,
            'acceleration_y': 2.0,
            'acceleration_z': 1.0
        }
        serializer = MotionTriggerRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid())

class AITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone='+1234567890',
            email='test@example.com',
            password='testpass123',
            full_name='Test User'
        )
        self.journey = Journey.objects.create(
            user=self.user,
            start_address='Start Address',
            destination_address='Destination Address'
        )
        self.client.force_authenticate(user=self.user)

    @patch('ai.services.ai_voice_service.process_voice_trigger')
    def test_trigger_voice_detection(self, mock_process):
        mock_process.return_value = (MagicMock(), None)
        url = reverse('ai:trigger-voice-detection')
        data = {
            'journey_id': str(self.journey.id),
            'safe_word': 'help',
            'confidence': 0.85
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('voice_event', response.data)

    @patch('ai.services.ai_motion_service.process_motion_event')
    def test_trigger_motion_detection(self, mock_process):
        mock_process.return_value = (MagicMock(), None)
        url = reverse('ai:trigger-motion-detection')
        data = {
            'journey_id': str(self.journey.id),
            'motion_type': 'crash',
            'acceleration_x': 5.0,
            'acceleration_y': 2.0,
            'acceleration_z': 1.0
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('motion_event', response.data)

    @patch('ai.services.ai_chat_service.create_chat_session')
    def test_create_chat_session(self, mock_create):
        mock_session = AIChatSession.objects.create(
            user=self.user,
            chat_type='journey_status'
        )
        mock_create.return_value = mock_session
        url = reverse('create_chat_session')
        data = {'chat_type': 'journey_status'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_chat_sessions_list(self):
        AIChatSession.objects.create(user=self.user, chat_type='help')
        url = reverse('chat_sessions')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)

    @patch('ai.services.ai_chat_service.process_chat_message')
    def test_send_chat_message(self, mock_process):
        session = AIChatSession.objects.create(user=self.user, chat_type='help')
        mock_message = AIChatMessage.objects.create(
            session=session,
            message_type='assistant',
            content='AI response'
        )
        mock_process.return_value = mock_message
        url = reverse('send_chat_message', kwargs={'session_id': session.id})
        data = {'message': 'Hello'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_submit_ai_feedback(self):
        url = reverse('submit_ai_feedback')
        data = {
            'feedback_type': 'voice_detection',
            'rating': 5,
            'comments': 'Excellent'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_voice_detection_history(self):
        VoiceDetectionEvent.objects.create(
            journey=self.journey,
            user=self.user,
            safe_word='help',
            confidence=0.8
        )
        url = reverse('voice_detection_history')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)

    def test_motion_detection_history(self):
        MotionDetectionEvent.objects.create(
            journey=self.journey,
            user=self.user,
            motion_type='crash',
            acceleration_x=5.0,
            acceleration_y=2.0,
            acceleration_z=1.0,
            impact_confidence=0.9
        )
        url = reverse('motion_detection_history')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)

    @patch('ai.services.ai_voice_service.analyze_audio_quality')
    def test_analyze_audio_quality(self, mock_analyze):
        mock_analyze.return_value = {'quality': 'good'}
        url = reverse('analyze_audio_quality')
        data = {'audio_data': 'base64data'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('ai.services.ai_voice_service.analyze_audio_for_emergency')
    @patch('alerts.services.AlertService.create_alert')
    def test_analyze_audio_emergency(self, mock_create_alert, mock_analyze):
        mock_analyze.return_value = (True, {'emergency': 'detected'})
        mock_alert = MagicMock()
        mock_alert.id = 'alert-uuid'
        mock_create_alert.return_value = mock_alert
        url = reverse('analyze_audio_emergency')
        data = {
            'audio_data': 'base64data',
            'journey_id': str(self.journey.id)
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['emergency_detected'])

    @patch('ai.services.spitch_audio_service.process_audio_chunk')
    def test_process_audio_chunk(self, mock_process):
        mock_process.return_value = ('Hello world', 0.95, {'info': 'test'})
        url = reverse('process_audio_chunk')
        data = {
            'audio_data': 'base64data',
            'keywords': ['help']
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('detected_text', response.data)

    def test_ai_service_status(self):
        url = reverse('ai_service_status')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('gemini_ai', response.data)
