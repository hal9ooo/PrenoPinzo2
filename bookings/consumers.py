"""
WebSocket consumer for real-time chat.
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import ChatMessage


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for family chat.
    All authenticated users join the same 'family_chat' group.
    """
    
    async def connect(self):
        self.room_group_name = 'family_chat'
        self.user = self.scope['user']
        
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Mark messages as read when user opens chat
        await self.mark_messages_read()
        
        # Send chat history
        history = await self.get_chat_history()
        await self.send(text_data=json.dumps({
            'type': 'chat_history',
            'messages': history
        }))
        
        # Notify others that user joined
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status',
                'username': self.user.username,
                'status': 'online'
            }
        )
    
    async def disconnect(self, close_code):
        # Notify others that user left
        if hasattr(self, 'user') and self.user.is_authenticated:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_status',
                    'username': self.user.username,
                    'status': 'offline'
                }
            )
        
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type', 'message')
        
        if message_type == 'message':
            content = data.get('content', '').strip()
            if content:
                # Save to database
                message_data = await self.save_message(content)
                
                # Broadcast to group
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'id': message_data['id'],
                        'content': content,
                        'sender': self.user.username,
                        'sender_family': message_data['sender_family'],
                        'timestamp': message_data['timestamp']
                    }
                )
        
        elif message_type == 'typing':
            # Broadcast typing indicator
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_indicator',
                    'username': self.user.username,
                    'is_typing': data.get('is_typing', False)
                }
            )
        
        elif message_type == 'mark_read':
            # Mark messages as read
            await self.mark_messages_read()
    
    async def chat_message(self, event):
        """Send message to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'message',
            'id': event['id'],
            'content': event['content'],
            'sender': event['sender'],
            'sender_family': event['sender_family'],
            'timestamp': event['timestamp']
        }))
    
    async def typing_indicator(self, event):
        """Send typing indicator to WebSocket"""
        # Don't send to the user who is typing
        if event['username'] != self.user.username:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'username': event['username'],
                'is_typing': event['is_typing']
            }))
    
    async def user_status(self, event):
        """Send user status to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'status',
            'username': event['username'],
            'status': event['status']
        }))
    
    @database_sync_to_async
    def save_message(self, content):
        """Save message to database"""
        message = ChatMessage.objects.create(
            sender=self.user,
            content=content
        )
        return {
            'id': message.id,
            'sender_family': self.user.profile.family_group,
            'timestamp': message.timestamp.strftime('%H:%M')
        }
    
    @database_sync_to_async
    def get_chat_history(self):
        """Get last 50 messages"""
        messages = ChatMessage.objects.select_related('sender', 'sender__profile').order_by('-timestamp')[:50]
        return [
            {
                'id': msg.id,
                'content': msg.content,
                'sender': msg.sender.username,
                'sender_family': msg.sender.profile.family_group,
                'timestamp': msg.timestamp.strftime('%H:%M'),
                'date': msg.timestamp.strftime('%d/%m/%Y')
            }
            for msg in reversed(messages)
        ]
    
    @database_sync_to_async
    def mark_messages_read(self):
        """Mark all messages not from this user as read"""
        ChatMessage.objects.exclude(sender=self.user).update(is_read=True)
