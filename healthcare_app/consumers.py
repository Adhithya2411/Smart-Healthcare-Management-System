# In healthcare_app/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone
from .models import Appointment, ChatMessage, User
from channels.db import database_sync_to_async

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.appointment_id = self.scope['url_route']['kwargs']['appointment_id']
        self.room_group_name = f'chat_{self.appointment_id}'
        user = self.scope['user']

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        user = self.scope['user']
        await self.save_message(user, self.appointment_id, message)
        await self.channel_layer.group_send(self.room_group_name,{'type': 'chat_message','message': message,'username': user.username})
    async def chat_message(self, event):
        message = event['message']
        username = event['username']
        await self.send(text_data=json.dumps({'message': message,'username': username}))
    @database_sync_to_async
    def check_authorization(self, user, appointment_id):
 
        try:
            appointment = Appointment.objects.select_related('timeslot', 'patient__user', 'timeslot__doctor__user').get(id=appointment_id)
            
            if user.role == 'patient' and appointment.patient.user == user:
                return True, appointment
            if user.role == 'doctor' and appointment.timeslot.doctor.user == user:
                return True, appointment
        except Appointment.DoesNotExist:
            return False, None
        return False, None
    @database_sync_to_async
    def save_message(self, user, appointment_id, message):
        appointment = Appointment.objects.get(id=appointment_id)
        ChatMessage.objects.create(user=user, appointment=appointment, message=message)