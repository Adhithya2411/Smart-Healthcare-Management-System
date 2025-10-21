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

        # --- DETAILED DEBUGGING BLOCK ---
        print("\n" + "="*50)
        print("          CHAT CONNECTION ATTEMPT          ")
        print("="*50)
        print(f"User: {user.username} (Authenticated: {user.is_authenticated})")
        print(f"Attempting to join room for Appointment ID: {self.appointment_id}")

        if not user.is_authenticated:
            print(">>> REASON FOR CLOSING: User is not authenticated.")
            await self.close()
            return

        is_authorized, appointment = await self.check_authorization(user, self.appointment_id)
        if not is_authorized:
            print(">>> REASON FOR CLOSING: User is not authorized for this appointment.")
            await self.close()
            return
        else:
            print("Authorization Check: PASSED")
            
        now = timezone.localtime()
        start_time = appointment.timeslot.start_time
        end_time = appointment.timeslot.end_time
        
        print(f"Current Time: {now}")
        print(f"Appt Start:   {start_time}")
        print(f"Appt End:     {end_time}")
        
        is_after_start = start_time <= now
        is_before_end = now <= end_time

        if not (is_after_start and is_before_end):
            print(f">>> REASON FOR CLOSING: Time check failed. (After Start: {is_after_start}, Before End: {is_before_end})")
            await self.close()
            return
        else:
            print("Time Check: PASSED")
        # --- END DEBUGGING BLOCK ---

        print("All checks passed. Accepting connection.")
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
            
            # The rest of the logic is the same, but now it's safer
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