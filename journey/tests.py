import json
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch, MagicMock
from decimal import Decimal

from .models import Journey, JourneyLocation, GroupJourney, Passenger, JourneyAlert
from users.models import User

User = get_user_model()

class JourneyModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone='+1234567890',
            email='test@example.com',
            password='testpass123',
            full_name='Test User'
        )

    def test_journey_creation(self):
        journey = Journey.objects.create(
            user=self.user,
            start_address='Start Address',
            destination_address='Destination Address',
            status='active'
        )
        self.assertEqual(journey.status, 'active')
        self.assertEqual(str(journey), f"{self.user.full_name} - Destination Address (active)")

    def test_journey_generate_code(self):
        journey = Journey.objects.create(
            user=self.user,
            start_address='Start',
            destination_address='End',
            journey_type='group'
        )
        self.assertIsNotNone(journey.journey_code)
        self.assertEqual(len(journey.journey_code), 6)

class JourneyLocationModelTest(TestCase):
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

    def test_journey_location_creation(self):
        location = JourneyLocation.objects.create(
            journey=self.journey,
            latitude=6.5244,
            longitude=3.3792,
            speed=50.0
        )
        self.assertEqual(location.latitude, 6.5244)
        self.assertEqual(str(location), f"{self.user.full_name} - {location.timestamp}")

class GroupJourneyModelTest(TestCase):
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
            destination_address='End',
            journey_type='group'
        )

    def test_group_journey_creation(self):
        group_journey = GroupJourney.objects.create(
            journey=self.journey,
            driver=self.user,
            vehicle_type='Bus',
            vehicle_capacity=50,
            route_name='Lagos-Abuja'
        )
        self.assertEqual(group_journey.route_name, 'Lagos-Abuja')
        self.assertEqual(str(group_journey), "Lagos-Abuja - Test User")

class PassengerModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone='+1234567890',
            email='test@example.com',
            password='testpass123',
            full_name='Test User'
        )
        self.driver = User.objects.create_user(
            phone='+0987654321',
            email='driver@example.com',
            password='testpass123',
            full_name='Driver User'
        )
        self.journey = Journey.objects.create(
            user=self.driver,
            start_address='Start',
            destination_address='End',
            journey_type='group'
        )
        group_journey = GroupJourney.objects.create(
            journey=self.journey,
            driver=self.driver,
            route_name='Test Route',
            vehicle_capacity=50
        )

    def test_passenger_creation(self):
        passenger = Passenger.objects.create(
            group_journey=self.group_journey,
            user=self.user,
            boarding_stop='Stop A',
            destination_stop='Stop B'
        )
        self.assertEqual(passenger.boarding_stop, 'Stop A')
        self.assertEqual(str(passenger), f"{self.user.full_name} - Test Route")

class JourneyAlertModelTest(TestCase):
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

    def test_journey_alert_creation(self):
        alert = JourneyAlert.objects.create(
            journey=self.journey,
            alert_type='panic',
            severity='high'
        )
        self.assertEqual(alert.alert_type, 'panic')
        self.assertEqual(str(alert), f"{self.user.full_name} - panic - active")

class JourneySerializerTest(TestCase):
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

    def test_journey_serializer(self):
        from .serializers import JourneySerializer
        serializer = JourneySerializer(self.journey)
        data = serializer.data
        self.assertIn('destination_address', data)
        self.assertEqual(data['destination_address'], 'End')

    def test_create_journey_serializer(self):
        from .serializers import CreateJourneySerializer
        data = {
            'start_address': 'New Start',
            'destination_address': 'New End'
        }
        serializer = CreateJourneySerializer(data=data, context={'request': MagicMock(user=self.user)})
        self.assertTrue(serializer.is_valid())

class JourneyTestCase(APITestCase):
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

    def test_create_journey(self):
        url = reverse('journey:journey-list')
        data = {
            'start_address': 'New Start',
            'destination_address': 'New End'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_get_user_journeys(self):
        url = reverse('journey:journey-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)

    def test_get_journey_detail(self):
        url = reverse('journey:journey-detail', kwargs={'journey_id': self.journey.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['destination_address'], 'Destination Address')

    def test_update_journey_status(self):
        url = reverse('journey:start-journey', kwargs={'journey_id': self.journey.id})
        data = {'status': 'active'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_add_journey_location(self):
        url = reverse('journey:update-location')
        data = {
            'latitude': 6.5244,
            'longitude': 3.3792,
            'speed': 45.0,
            'journey_id': str(self.journey.id)
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_group_journey(self):
        url = reverse('journey:create-group-journey')
        data = {
            'journey': str(self.journey.id),
            'vehicle_type': 'Bus',
            'vehicle_capacity': 50,
            'route_name': 'Test Route'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_join_group_journey(self):
        driver = User.objects.create_user(
            phone='+0987654321',
            email='driver@example.com',
            password='testpass123',
            full_name='Driver'
        )
        group_journey = GroupJourney.objects.create(
            journey=self.journey,
            driver=driver,
            route_name='Test Route',
            vehicle_capacity=50
        )
        url = reverse('journey:join-group-journey')
        data = {
            'group_journey_id': str(group_journey.id),
            'boarding_stop': 'Stop A',
            'destination_stop': 'Stop B'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_get_passengers(self):
        driver = User.objects.create_user(
            phone='+0987654321',
            email='driver@example.com',
            password='testpass123',
            full_name='Driver'
        )
        group_journey = GroupJourney.objects.create(
            journey=self.journey,
            driver=driver,
            route_name='Test Route'
        )
        url = reverse('journey:group-journey-passengers', kwargs={'journey_id': self.journey.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
