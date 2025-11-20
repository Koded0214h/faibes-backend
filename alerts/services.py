import json
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import Alert, AlertNotification, SafetyNetworkMember, Journey
from utils.notifications import send_sms, send_whatsapp, send_push_notification

User = get_user_model()

class AlertService:
    """Service for handling alert creation and notifications"""
    
    @staticmethod
    def create_alert(journey, alert_type, triggered_by, **kwargs):
        """Create a new alert and trigger notifications"""
        from .serializers import AlertSerializer
        
        alert_data = {
            'journey': journey,
            'alert_type': alert_type,
            'triggered_by': triggered_by,
            'severity': kwargs.get('severity', 'high'),
            'trigger_data': kwargs.get('trigger_data', {}),
            'location_lat': kwargs.get('location_lat'),
            'location_lng': kwargs.get('location_lng'),
            'location_address': kwargs.get('location_address', ''),
            'battery_level': kwargs.get('battery_level'),
            'network_strength': kwargs.get('network_strength'),
            'device_info': kwargs.get('device_info', {})
        }
        
        alert = Alert.objects.create(**alert_data)
        
        # Trigger notifications
        AlertService.notify_safety_network(alert)
        
        # Broadcast via WebSocket
        AlertService.broadcast_alert(alert)
        
        return alert
    
    @staticmethod
    def notify_safety_network(alert):
        """Notify all safety network members about the alert"""
        user = alert.journey.user
        safety_network = user.safety_network
        
        for phone_number in safety_network:
            try:
                # Get or create safety network member
                member, created = SafetyNetworkMember.objects.get_or_create(
                    user=user,
                    member_phone=phone_number,
                    defaults={'is_active': True}
                )
                
                if not member.is_active:
                    continue
                
                # Create notification messages
                message = AlertService.create_alert_message(alert, member)
                
                # Send SMS if enabled
                if member.receive_sms:
                    AlertService.send_sms_notification(alert, member, message)
                
                # Send WhatsApp if enabled
                if member.receive_whatsapp:
                    AlertService.send_whatsapp_notification(alert, member, message)
                
                # Send push notification if enabled
                if member.receive_push:
                    AlertService.send_push_notification(alert, member, message)
                
                # Update last notified timestamp
                member.last_notified = timezone.now()
                member.save()
                
            except Exception as e:
                print(f"Failed to notify {phone_number}: {str(e)}")
    
    @staticmethod
    def create_alert_message(alert, member):
        """Create alert message based on alert type"""
        user = alert.journey.user
        location_info = ""
        
        if alert.location_lat and alert.location_lng:
            location_info = f" at https://maps.google.com/?q={alert.location_lat},{alert.location_lng}"
        
        messages = {
            'panic_button': f"🚨 PANIC ALERT! {user.full_name} has triggered a panic alert{location_info}. Battery: {alert.battery_level or 'Unknown'}%",
            'voice_trigger': f"🔊 VOICE ALERT! {user.full_name}'s safe word was detected{location_info}. Check their status immediately.",
            'motion_crash': f"💥 CRASH DETECTED! Possible accident involving {user.full_name}{location_info}. Emergency response needed.",
            'route_deviation': f"🛣️ ROUTE DEVIATION! {user.full_name} has gone off route{location_info}. Check if everything is okay.",
            'no_movement': f"⏰ NO MOVEMENT! {user.full_name} hasn't moved for an extended period{location_info}. Please check on them.",
            'low_battery': f"🔋 LOW BATTERY! {user.full_name}'s device battery is low ({alert.battery_level}%){location_info}.",
        }
        
        return messages.get(alert.alert_type, 
            f"🚨 ALERT! {user.full_name} has a {alert.alert_type} alert{location_info}. Please check on them.")
    
    @staticmethod
    def send_sms_notification(alert, member, message):
        """Send SMS notification"""
        try:
            notification = AlertNotification.objects.create(
                alert=alert,
                recipient_phone=member.member_phone,
                notification_type='sms',
                message=message
            )
            
            # Use Twilio or other SMS service
            success, provider_id = send_sms(member.member_phone, message)
            
            if success:
                notification.status = 'sent'
                notification.provider_message_id = provider_id
                notification.sent_at = timezone.now()
            else:
                notification.status = 'failed'
                notification.error_message = "SMS sending failed"
            
            notification.save()
            
        except Exception as e:
            print(f"SMS notification failed: {str(e)}")
    
    @staticmethod
    def send_whatsapp_notification(alert, member, message):
        """Send WhatsApp notification"""
        try:
            notification = AlertNotification.objects.create(
                alert=alert,
                recipient_phone=member.member_phone,
                notification_type='whatsapp',
                message=message
            )
            
            # Use Twilio WhatsApp or other service
            success, provider_id = send_whatsapp(member.member_phone, message)
            
            if success:
                notification.status = 'sent'
                notification.provider_message_id = provider_id
                notification.sent_at = timezone.now()
            else:
                notification.status = 'failed'
                notification.error_message = "WhatsApp sending failed"
            
            notification.save()
            
        except Exception as e:
            print(f"WhatsApp notification failed: {str(e)}")
    
    @staticmethod
    def send_push_notification(alert, member, message):
        """Send push notification to WebSocket connections"""
        try:
            # Find user by phone number for push notifications
            try:
                recipient_user = User.objects.get(phone=member.member_phone)
            except User.DoesNotExist:
                return  # User not in system, can't send push
            
            notification = AlertNotification.objects.create(
                alert=alert,
                recipient_user=recipient_user,
                notification_type='push',
                message=message
            )
            
            # Broadcast to user's WebSocket connections
            AlertService.broadcast_to_user(recipient_user, 'alert', {
                'alert_id': str(alert.id),
                'type': alert.alert_type,
                'message': message,
                'severity': alert.severity,
                'user_name': alert.journey.user.full_name,
                'location': {
                    'lat': float(alert.location_lat) if alert.location_lat else None,
                    'lng': float(alert.location_lng) if alert.location_lng else None,
                } if alert.location_lat and alert.location_lng else None
            })
            
            notification.status = 'sent'
            notification.sent_at = timezone.now()
            notification.save()
            
        except Exception as e:
            print(f"Push notification failed: {str(e)}")
    
    @staticmethod
    def broadcast_alert(alert):
        """Broadcast alert via WebSocket to relevant parties"""
        from .serializers import AlertSerializer
        
        alert_data = AlertSerializer(alert).data
        
        # Broadcast to user
        AlertService.broadcast_to_user(alert.journey.user, 'alert', alert_data)
        
        # Broadcast to safety network
        AlertService.broadcast_to_safety_network(alert.journey.user, 'alert', alert_data)
        
        # Broadcast to journey group
        AlertService.broadcast_to_journey(alert.journey, 'alert', alert_data)
    
    @staticmethod
    def broadcast_to_user(user, message_type, data):
        """Broadcast message to a specific user"""
        channel_layer = get_channel_layer()
        group_name = f"user_{user.id}"
        
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': f'{message_type}_message',
                message_type: data,
                'timestamp': timezone.now().isoformat()
            }
        )
    
    @staticmethod
    def broadcast_to_safety_network(user, message_type, data):
        """Broadcast message to user's safety network"""
        channel_layer = get_channel_layer()
        group_name = f"safety_network_{user.id}"
        
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': f'{message_type}_message',
                message_type: data,
                'timestamp': timezone.now().isoformat()
            }
        )
    
    @staticmethod
    def broadcast_to_journey(journey, message_type, data):
        """Broadcast message to journey subscribers"""
        channel_layer = get_channel_layer()
        group_name = f"journey_{journey.id}"
        
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': f'{message_type}_message',
                message_type: data,
                'timestamp': timezone.now().isoformat()
            }
        )
    
    @staticmethod
    def broadcast_location_update(journey, location_data):
        """Broadcast location update to relevant parties"""
        # Broadcast to user
        AlertService.broadcast_to_user(journey.user, 'location_update', {
            'journey_id': str(journey.id),
            'location': location_data
        })
        
        # Broadcast to safety network
        AlertService.broadcast_to_safety_network(journey.user, 'location_update', {
            'journey_id': str(journey.id),
            'location': location_data
        })
        
        # Broadcast to journey group
        AlertService.broadcast_to_journey(journey, 'location_update', {
            'journey_id': str(journey.id),
            'location': location_data
        })

class PanicButtonService:
    """Service for handling panic button functionality"""
    
    @staticmethod
    def handle_panic_button(journey, user, **context):
        """Handle panic button press"""
        # Create panic button press record
        from .models import PanicButtonPress
        press = PanicButtonPress.objects.create(
            journey=journey,
            user=user,
            press_count=context.get('press_count', 1),
            press_duration=context.get('press_duration'),
            location_lat=context.get('location_lat'),
            location_lng=context.get('location_lng'),
            battery_level=context.get('battery_level')
        )
        
        # Create alert
        alert = AlertService.create_alert(
            journey=journey,
            alert_type='panic_button',
            triggered_by=user,
            severity='critical',
            location_lat=context.get('location_lat'),
            location_lng=context.get('location_lng'),
            battery_level=context.get('battery_level'),
            trigger_data={
                'press_count': context.get('press_count', 1),
                'press_duration': context.get('press_duration'),
                'is_emergency': True
            }
        )
        
        return alert, press
    
    @staticmethod
    def cancel_panic_alert(alert, user, reason=""):
        """Cancel a panic alert"""
        alert.status = 'cancelled'
        alert.resolved_by = user
        alert.resolved_at = timezone.now()
        alert.resolution_notes = f"Cancelled by user: {reason}"
        alert.save()
        
        # Update related panic button press
        from .models import PanicButtonPress
        PanicButtonPress.objects.filter(
            journey=alert.journey,
            user=user,
            is_cancelled=False
        ).update(
            is_cancelled=True,
            cancelled_at=timezone.now(),
            cancellation_reason=reason
        )
        
        # Broadcast cancellation
        AlertService.broadcast_alert(alert)
        
        return alert