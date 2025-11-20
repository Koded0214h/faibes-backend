from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Alert, AlertNotification, SafetyNetworkMember, PanicButtonPress
from .serializers import (
    AlertSerializer, CreateAlertSerializer, AlertNotificationSerializer,
    SafetyNetworkMemberSerializer, CreateSafetyNetworkMemberSerializer,
    PanicButtonPressSerializer, CreatePanicButtonPressSerializer,
    AlertStatusUpdateSerializer
)
from .services import AlertService, PanicButtonService
from journey.models import Journey

@api_view(['GET'])
def user_alerts(request):
    """Get all alerts for user's journeys"""
    try:
        # Get alerts for journeys where user is involved
        user_journeys = Journey.objects.filter(user=request.user)
        alerts = Alert.objects.filter(journey__in=user_journeys).order_by('-created_at')
        
        serializer = AlertSerializer(alerts, many=True)
        return Response(serializer.data)
    
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def trigger_alert(request):
    """Trigger a new alert (for voice, motion, etc.)"""
    try:
        serializer = CreateAlertSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            alert = serializer.save()
            
            # Use service to handle notifications
            AlertService.notify_safety_network(alert)
            AlertService.broadcast_alert(alert)
            
            return Response(
                AlertSerializer(alert).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def trigger_panic_alert(request):
    """Trigger a panic alert"""
    try:
        serializer = CreatePanicButtonPressSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            journey = serializer.validated_data['journey']
            
            # Verify user owns the journey
            if journey.user != request.user:
                return Response(
                    {'error': 'Not authorized for this journey'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Use service to handle panic alert
            alert, press = PanicButtonService.handle_panic_button(
                journey=journey,
                user=request.user,
                location_lat=serializer.validated_data.get('location_lat'),
                location_lng=serializer.validated_data.get('location_lng'),
                battery_level=serializer.validated_data.get('battery_level'),
                press_count=serializer.validated_data.get('press_count', 1),
                press_duration=serializer.validated_data.get('press_duration')
            )
            
            return Response({
                'message': 'Panic alert triggered successfully',
                'alert': AlertSerializer(alert).data,
                'press': PanicButtonPressSerializer(press).data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def cancel_panic_alert(request, alert_id):
    """Cancel a panic alert (false alarm)"""
    try:
        alert = get_object_or_404(Alert, id=alert_id)
        
        # Verify user owns the alert
        if alert.journey.user != request.user:
            return Response(
                {'error': 'Not authorized for this alert'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        reason = request.data.get('reason', 'User cancelled')
        alert = PanicButtonService.cancel_panic_alert(alert, request.user, reason)
        
        return Response({
            'message': 'Panic alert cancelled successfully',
            'alert': AlertSerializer(alert).data
        })
    
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['PUT'])
def update_alert_status(request, alert_id):
    """Update alert status (resolve, mark as false alarm, etc.)"""
    try:
        alert = get_object_or_404(Alert, id=alert_id)
        
        # Verify user is involved in the alert (either triggered by or journey owner)
        if alert.triggered_by != request.user and alert.journey.user != request.user:
            return Response(
                {'error': 'Not authorized for this alert'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = AlertStatusUpdateSerializer(
            data=request.data,
            context={'alert': alert}
        )
        
        if serializer.is_valid():
            alert.status = serializer.validated_data['status']
            
            if serializer.validated_data.get('resolution_notes'):
                alert.resolution_notes = serializer.validated_data['resolution_notes']
            
            if alert.status in ['resolved', 'false_alarm', 'cancelled']:
                alert.resolved_by = request.user
                alert.resolved_at = timezone.now()
            
            alert.save()
            
            # Broadcast update
            AlertService.broadcast_alert(alert)
            
            return Response(AlertSerializer(alert).data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET', 'POST'])
def safety_network_members(request):
    """List and add safety network members"""
    try:
        if request.method == 'GET':
            members = SafetyNetworkMember.objects.filter(
                user=request.user, 
                is_active=True
            ).order_by('-is_primary', 'member_name')
            
            serializer = SafetyNetworkMemberSerializer(members, many=True)
            return Response(serializer.data)
        
        elif request.method == 'POST':
            serializer = CreateSafetyNetworkMemberSerializer(data=request.data)
            
            if serializer.is_valid():
                member = SafetyNetworkMember.objects.create(
                    user=request.user,
                    **serializer.validated_data
                )
                
                # Update user's safety network list
                user = request.user
                if member.member_phone not in user.safety_network:
                    user.safety_network.append(member.member_phone)
                    user.save()
                
                return Response(
                    SafetyNetworkMemberSerializer(member).data,
                    status=status.HTTP_201_CREATED
                )
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['PUT', 'DELETE'])
def safety_network_member_detail(request, member_id):
    """Update or remove safety network member"""
    try:
        member = get_object_or_404(
            SafetyNetworkMember, 
            id=member_id, 
            user=request.user
        )
        
        if request.method == 'PUT':
            serializer = SafetyNetworkMemberSerializer(
                member, 
                data=request.data, 
                partial=True
            )
            
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        elif request.method == 'DELETE':
            # Soft delete by marking as inactive
            member.is_active = False
            member.save()
            
            # Remove from user's safety network list
            user = request.user
            if member.member_phone in user.safety_network:
                user.safety_network.remove(member.member_phone)
                user.save()
            
            return Response(
                {'message': 'Safety network member removed successfully'},
                status=status.HTTP_200_OK
            )
    
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
def alert_notifications(request, alert_id):
    """Get notifications for a specific alert"""
    try:
        alert = get_object_or_404(Alert, id=alert_id)
        
        # Verify user has access to this alert
        if alert.triggered_by != request.user and alert.journey.user != request.user:
            return Response(
                {'error': 'Not authorized for this alert'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        notifications = alert.notifications.all().order_by('-created_at')
        serializer = AlertNotificationSerializer(notifications, many=True)
        
        return Response(serializer.data)
    
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
def panic_button_history(request):
    """Get user's panic button press history"""
    try:
        presses = PanicButtonPress.objects.filter(
            user=request.user
        ).order_by('-created_at')[:50]  # Last 50 presses
        
        serializer = PanicButtonPressSerializer(presses, many=True)
        return Response(serializer.data)
    
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )