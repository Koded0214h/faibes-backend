from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404

from .models import Journey, JourneyLocation, GroupJourney, Passenger, JourneyAlert
from .serializers import (
    JourneySerializer, CreateJourneySerializer, GroupJourneySerializer,
    CreateGroupJourneySerializer, PassengerSerializer, JoinGroupJourneySerializer,
    LocationUpdateSerializer, JourneyStatusSerializer, JourneyAlertSerializer
)

@api_view(['GET', 'POST'])
def journey_list(request):
    """List user's journeys or create a new journey"""
    try:
        if request.method == 'GET':
            journeys = Journey.objects.filter(user=request.user).order_by('-created_at')
            serializer = JourneySerializer(journeys, many=True)
            return Response(serializer.data)
        
        elif request.method == 'POST':
            serializer = CreateJourneySerializer(
                data=request.data, 
                context={'request': request}
            )
            if serializer.is_valid():
                journey = serializer.save()
                return Response(
                    JourneySerializer(journey).data,
                    status=status.HTTP_201_CREATED
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET', 'PUT', 'DELETE'])
def journey_detail(request, journey_id):
    """Get, update, or delete a specific journey"""
    try:
        journey = get_object_or_404(Journey, id=journey_id, user=request.user)
        
        if request.method == 'GET':
            serializer = JourneySerializer(journey)
            return Response(serializer.data)
        
        elif request.method == 'PUT':
            serializer = CreateJourneySerializer(
                journey, 
                data=request.data, 
                partial=True,
                context={'request': request}
            )
            if serializer.is_valid():
                serializer.save()
                return Response(JourneySerializer(journey).data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        elif request.method == 'DELETE':
            # Soft delete by cancelling
            if journey.status in ['scheduled', 'active']:
                journey.status = 'cancelled'
                journey.save()
            return Response(
                {'message': 'Journey cancelled successfully'},
                status=status.HTTP_200_OK
            )
    
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def start_journey(request, journey_id):
    """Start a scheduled journey"""
    try:
        journey = get_object_or_404(Journey, id=journey_id, user=request.user)
        
        if journey.status != 'scheduled':
            return Response(
                {'error': 'Journey is not in scheduled state'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        journey.status = 'active'
        journey.actual_start = timezone.now()
        journey.save()
        
        return Response({
            'message': 'Journey started successfully',
            'journey': JourneySerializer(journey).data
        })
    
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def complete_journey(request, journey_id):
    """Mark journey as completed"""
    try:
        journey = get_object_or_404(Journey, id=journey_id, user=request.user)
        
        if journey.status != 'active':
            return Response(
                {'error': 'Only active journeys can be completed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        journey.status = 'completed'
        journey.actual_arrival = timezone.now()
        journey.save()
        
        return Response({
            'message': 'Journey completed successfully',
            'journey': JourneySerializer(journey).data
        })
    
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def update_location(request):
    """Update current location for an active journey"""
    try:
        serializer = LocationUpdateSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            journey = serializer.context['journey']
            
            # Verify user owns the journey
            if journey.user != request.user:
                return Response(
                    {'error': 'Not authorized for this journey'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Create location record
            location_data = serializer.validated_data.copy()
            location_data.pop('journey_id')
            location = JourneyLocation.objects.create(
                journey=journey,
                **location_data
            )
            
            # Broadcast to safety network via WebSocket (will implement in alerts app)
            # TODO: Implement WebSocket broadcasting
            
            return Response({
                'message': 'Location updated successfully',
                'location': {
                    'latitude': location.latitude,
                    'longitude': location.longitude,
                    'timestamp': location.timestamp
                }
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def create_group_journey(request):
    """Create a group journey (for drivers/operators)"""
    try:
        serializer = CreateGroupJourneySerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            with transaction.atomic():
                group_journey = serializer.save()
                
                # Generate journey code for the base journey
                group_journey.journey.journey_code = group_journey.journey.generate_journey_code()
                group_journey.journey.save()
            
            return Response(
                GroupJourneySerializer(group_journey).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def join_group_journey(request):
    """Join a group journey using journey code"""
    try:
        serializer = JoinGroupJourneySerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            journey = serializer.context['journey']
            group_journey = journey.group_journey
            
            # Check if user is already a passenger
            if Passenger.objects.filter(group_journey=group_journey, user=request.user).exists():
                return Response(
                    {'error': 'Already joined this journey'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check capacity
            if group_journey.current_passengers >= group_journey.max_passengers:
                return Response(
                    {'error': 'Journey is full'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            with transaction.atomic():
                # Create passenger record
                passenger = Passenger.objects.create(
                    group_journey=group_journey,
                    user=request.user,
                    boarding_stop=serializer.validated_data['boarding_stop'],
                    destination_stop=serializer.validated_data['destination_stop']
                )
                
                # Update passenger count
                group_journey.current_passengers += 1
                group_journey.save()
                
                # Create personal journey record for the passenger
                personal_journey = Journey.objects.create(
                    user=request.user,
                    journey_type='group',
                    journey_code=journey.journey_code,
                    driver_name=group_journey.driver.full_name,
                    driver_phone=group_journey.driver.phone,
                    vehicle_plate=journey.vehicle_plate,
                    start_address=serializer.validated_data['boarding_stop'],
                    destination_address=serializer.validated_data['destination_stop'],
                    safety_network=request.user.safety_network,
                    status='scheduled'
                )
            
            return Response({
                'message': 'Successfully joined group journey',
                'passenger': PassengerSerializer(passenger).data,
                'journey': JourneySerializer(personal_journey).data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
def group_journey_passengers(request, journey_id):
    """Get passengers for a group journey (driver only)"""
    try:
        journey = get_object_or_404(Journey, id=journey_id)
        
        # Verify requester is the driver
        if journey.user != request.user:
            return Response(
                {'error': 'Not authorized to view passengers'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not hasattr(journey, 'group_journey'):
            return Response(
                {'error': 'Not a group journey'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        passengers = journey.group_journey.passengers.all()
        serializer = PassengerSerializer(passengers, many=True)
        
        return Response(serializer.data)
    
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
def journey_alerts(request, journey_id):
    """Get alerts for a specific journey"""
    try:
        journey = get_object_or_404(Journey, id=journey_id, user=request.user)
        alerts = journey.alerts.all().order_by('-created_at')
        serializer = JourneyAlertSerializer(alerts, many=True)
        
        return Response(serializer.data)
    
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
def active_journey(request):
    """Get user's currently active journey"""
    try:
        active_journey = Journey.objects.filter(
            user=request.user,
            status='active'
        ).first()
        
        if not active_journey:
            return Response(
                {'message': 'No active journey'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = JourneySerializer(active_journey)
        return Response(serializer.data)
    
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )