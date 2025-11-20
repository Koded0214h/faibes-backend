import json
import uuid
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import WebSocketConnection, Alert, Journey

User = get_user_model()

class AlertConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        
        if self.user.is_anonymous:
            await self.close()
            return
        
        self.connection_id = str(uuid.uuid4())
        self.user_group = f"user_{self.user.id}"
        self.safety_network_group = f"safety_network_{self.user.id}"
        
        # Join user group
        await self.channel_layer.group_add(
            self.user_group,
            self.channel_name
        )
        
        # Store connection in database
        await self.store_connection()
        
        await self.accept()
        
        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'WebSocket connection established',
            'connection_id': self.connection_id,
            'timestamp': timezone.now().isoformat()
        }))

    async def disconnect(self, close_code):
        # Leave groups
        await self.channel_layer.group_discard(
            self.user_group,
            self.channel_name
        )
        
        # Mark connection as inactive
        await self.mark_connection_inactive()

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'subscribe_journey':
                await self.handle_journey_subscription(data)
            elif message_type == 'subscribe_safety_network':
                await self.handle_safety_network_subscription(data)
            elif message_type == 'ping':
                await self.send_pong()
            else:
                await self.send_error("Unknown message type")
                
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON")
        except Exception as e:
            await self.send_error(str(e))

    async def handle_journey_subscription(self, data):
        """Handle journey subscription requests"""
        journey_id = data.get('journey_id')
        
        if journey_id:
            journey = await self.get_journey(journey_id)
            if journey and (journey.user == self.user or await self.is_safety_network_member(journey.user)):
                group_name = f"journey_{journey_id}"
                await self.channel_layer.group_add(
                    group_name,
                    self.channel_name
                )
                await self.update_subscribed_journeys([journey_id])
                
                await self.send(text_data=json.dumps({
                    'type': 'subscription_success',
                    'message': f'Subscribed to journey {journey_id}',
                    'journey_id': journey_id,
                    'timestamp': timezone.now().isoformat()
                }))

    async def handle_safety_network_subscription(self, data):
        """Handle safety network subscription"""
        user_id = data.get('user_id')
        
        if user_id and await self.is_safety_network_member_id(user_id):
            group_name = f"safety_network_{user_id}"
            await self.channel_layer.group_add(
                group_name,
                self.channel_name
            )
            await self.update_subscribed_users([user_id])
            
            await self.send(text_data=json.dumps({
                'type': 'subscription_success',
                'message': f'Subscribed to safety network of user {user_id}',
                'user_id': user_id,
                'timestamp': timezone.now().isoformat()
            }))

    async def send_pong(self):
        await self.send(text_data=json.dumps({
            'type': 'pong',
            'timestamp': timezone.now().isoformat()
        }))

    async def send_error(self, error_message):
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': error_message,
            'timestamp': timezone.now().isoformat()
        }))

    # Message handlers for different types of broadcasts
    async def alert_message(self, event):
        """Handle alert messages"""
        await self.send(text_data=json.dumps({
            'type': 'alert',
            'alert': event['alert'],
            'timestamp': event['timestamp']
        }))

    async def location_update(self, event):
        """Handle location update messages"""
        await self.send(text_data=json.dumps({
            'type': 'location_update',
            'location': event['location'],
            'journey_id': event['journey_id'],
            'timestamp': event['timestamp']
        }))

    async def panic_alert(self, event):
        """Handle panic alert messages"""
        await self.send(text_data=json.dumps({
            'type': 'panic_alert',
            'alert': event['alert'],
            'user_info': event['user_info'],
            'timestamp': event['timestamp']
        }))

    async def journey_status(self, event):
        """Handle journey status updates"""
        await self.send(text_data=json.dumps({
            'type': 'journey_status',
            'journey_id': event['journey_id'],
            'status': event['status'],
            'timestamp': event['timestamp']
        }))

    # Database operations
    @database_sync_to_async
    def store_connection(self):
        """Store WebSocket connection in database"""
        return WebSocketConnection.objects.create(
            user=self.user,
            connection_id=self.connection_id,
            user_agent=self.scope.get('headers', {}).get(b'user-agent', b'').decode(),
            ip_address=self.scope.get('client')[0] if self.scope.get('client') else None
        )

    @database_sync_to_async
    def mark_connection_inactive(self):
        """Mark connection as inactive"""
        WebSocketConnection.objects.filter(
            connection_id=self.connection_id
        ).update(
            is_active=False,
            disconnected_at=timezone.now()
        )

    @database_sync_to_async
    def update_subscribed_journeys(self, journey_ids):
        """Update subscribed journeys for this connection"""
        WebSocketConnection.objects.filter(
            connection_id=self.connection_id
        ).update(
            subscribed_journeys=journey_ids
        )

    @database_sync_to_async
    def update_subscribed_users(self, user_ids):
        """Update subscribed users for this connection"""
        WebSocketConnection.objects.filter(
            connection_id=self.connection_id
        ).update(
            subscribed_users=user_ids
        )

    @database_sync_to_async
    def get_journey(self, journey_id):
        """Get journey by ID"""
        try:
            return Journey.objects.get(id=journey_id)
        except Journey.DoesNotExist:
            return None

    @database_sync_to_async
    def is_safety_network_member(self, user):
        """Check if current user is in the safety network of another user"""
        return user.safety_network_members.filter(
            member_phone=self.user.phone,
            is_active=True
        ).exists()

    @database_sync_to_async
    def is_safety_network_member_id(self, user_id):
        """Check if current user is in the safety network of another user by ID"""
        try:
            user = User.objects.get(id=user_id)
            return user.safety_network_members.filter(
                member_phone=self.user.phone,
                is_active=True
            ).exists()
        except User.DoesNotExist:
            return False