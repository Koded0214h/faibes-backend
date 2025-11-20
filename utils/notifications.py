import os
import logging
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

class NotificationService:
    """Service for sending notifications via SMS, WhatsApp, and push"""
    
    def __init__(self):
        self.twilio_client = None
        self.init_twilio()
    
    def init_twilio(self):
        """Initialize Twilio client if credentials are available"""
        if (settings.TWILIO_ACCOUNT_SID and 
            settings.TWILIO_AUTH_TOKEN and 
            settings.TWILIO_PHONE_NUMBER):
            try:
                self.twilio_client = Client(
                    settings.TWILIO_ACCOUNT_SID, 
                    settings.TWILIO_AUTH_TOKEN
                )
                logger.info("Twilio client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {str(e)}")
                self.twilio_client = None
    
    def send_sms(self, to_phone, message):
        """
        Send SMS using Twilio
        Returns: (success: bool, provider_message_id: str)
        """
        if not self.twilio_client:
            logger.error("Twilio client not initialized")
            return False, "twilio_not_configured"
        
        try:
            # Format phone number (ensure it starts with +)
            if not to_phone.startswith('+'):
                to_phone = f"+{to_phone}"
            
            message = self.twilio_client.messages.create(
                body=message,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=to_phone
            )
            
            logger.info(f"SMS sent to {to_phone}: {message.sid}")
            return True, message.sid
            
        except TwilioRestException as e:
            logger.error(f"Twilio SMS error: {e.code} - {e.msg}")
            return False, f"twilio_error_{e.code}"
        except Exception as e:
            logger.error(f"SMS sending failed: {str(e)}")
            return False, "unknown_error"
    
    def send_whatsapp(self, to_phone, message):
        """
        Send WhatsApp message using Twilio
        Returns: (success: bool, provider_message_id: str)
        """
        if not self.twilio_client:
            logger.error("Twilio client not initialized")
            return False, "twilio_not_configured"
        
        try:
            # Format phone number for WhatsApp
            if not to_phone.startswith('+'):
                to_phone = f"+{to_phone}"
            
            # Twilio WhatsApp format: whatsapp:+1234567890
            whatsapp_to = f"whatsapp:{to_phone}"
            whatsapp_from = f"whatsapp:{settings.TWILIO_PHONE_NUMBER}"
            
            message = self.twilio_client.messages.create(
                body=message,
                from_=whatsapp_from,
                to=whatsapp_to
            )
            
            logger.info(f"WhatsApp message sent to {to_phone}: {message.sid}")
            return True, message.sid
            
        except TwilioRestException as e:
            logger.error(f"Twilio WhatsApp error: {e.code} - {e.msg}")
            return False, f"twilio_error_{e.code}"
        except Exception as e:
            logger.error(f"WhatsApp sending failed: {str(e)}")
            return False, "unknown_error"
    
    def send_push_notification(self, user, title, message, data=None):
        """
        Send push notification (placeholder for FCM/APNs)
        In a real implementation, this would integrate with Firebase Cloud Messaging
        """
        try:
            # TODO: Implement actual push notification service
            # For now, we'll log and return success for demo purposes
            logger.info(f"Push notification to {user.phone}: {title} - {message}")
            
            # In a real implementation, you would:
            # 1. Get user's FCM tokens
            # 2. Send to FCM/APNs
            # 3. Handle responses
            
            return True, "push_sent_demo"
            
        except Exception as e:
            logger.error(f"Push notification failed: {str(e)}")
            return False, "push_error"
    
    def send_emergency_alert(self, user, alert_type, location=None, additional_data=None):
        """
        Send emergency alert to user's safety network
        """
        try:
            safety_network = user.safety_network
            results = {
                'sms_sent': [],
                'whatsapp_sent': [],
                'push_sent': [],
                'failed': []
            }
            
            # Create alert message
            message = self._create_emergency_message(user, alert_type, location)
            
            for phone_number in safety_network:
                # Send SMS
                sms_success, sms_id = self.send_sms(phone_number, message)
                if sms_success:
                    results['sms_sent'].append(phone_number)
                else:
                    results['failed'].append({'phone': phone_number, 'type': 'sms', 'error': sms_id})
                
                # Send WhatsApp
                whatsapp_success, whatsapp_id = self.send_whatsapp(phone_number, message)
                if whatsapp_success:
                    results['whatsapp_sent'].append(phone_number)
                else:
                    results['failed'].append({'phone': phone_number, 'type': 'whatsapp', 'error': whatsapp_id})
            
            logger.info(f"Emergency alert sent for user {user.phone}: {results}")
            return True, results
            
        except Exception as e:
            logger.error(f"Emergency alert failed: {str(e)}")
            return False, str(e)
    
    def _create_emergency_message(self, user, alert_type, location=None):
        """Create emergency message based on alert type"""
        base_message = f"🚨 FAIBES ALERT: {user.full_name} "
        
        messages = {
            'panic_button': "has triggered a panic button!",
            'voice_trigger': "detected safe word! Possible emergency!",
            'motion_crash': "may have been in an accident!",
            'route_deviation': "has deviated from their route!",
            'no_movement': "has not moved for an extended period!",
            'low_battery': "device battery is critically low!",
        }
        
        message = base_message + messages.get(alert_type, "has an emergency!")
        
        # Add location if available
        if location and location.get('lat') and location.get('lng'):
            maps_url = f"https://maps.google.com/?q={location['lat']},{location['lng']}"
            message += f" Location: {maps_url}"
        
        # Add contact information
        message += f" Contact: {user.phone}"
        
        return message

# Global instance
notification_service = NotificationService()

# Convenience functions
def send_sms(to_phone, message):
    """Convenience function for sending SMS"""
    return notification_service.send_sms(to_phone, message)

def send_whatsapp(to_phone, message):
    """Convenience function for sending WhatsApp"""
    return notification_service.send_whatsapp(to_phone, message)

def send_push_notification(user, title, message, data=None):
    """Convenience function for sending push notifications"""
    return notification_service.send_push_notification(user, title, message, data)

def send_emergency_alert(user, alert_type, location=None, additional_data=None):
    """Convenience function for sending emergency alerts"""
    return notification_service.send_emergency_alert(user, alert_type, location, additional_data)