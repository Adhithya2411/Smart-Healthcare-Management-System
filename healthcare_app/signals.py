from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from .models import Prescription, Appointment, Notification

@receiver(post_save, sender=Prescription)
def create_prescription_notification(sender, instance, created, **kwargs):
    """
    Create a notification when a doctor answers a help request.
    """
    if created:
        patient_user = instance.help_request.patient.user
        doctor_user = instance.help_request.doctor.user
        
        Notification.objects.create(
            user=patient_user,
            message=f"Dr. {doctor_user.get_full_name()} has answered your help request.",
            link=reverse('patient_dashboard')
        )

@receiver(post_save, sender=Appointment)
def create_appointment_notification(sender, instance, created, **kwargs):
    """
    Create a notification when a patient books an appointment.
    """
    if created:
        patient_user = instance.patient.user
        doctor_user = instance.timeslot.doctor.user
        
        Notification.objects.create(
            user=doctor_user,
            message=f"Patient {patient_user.get_full_name()} has booked an appointment with you.",
            link=reverse('doctor_dashboard') 
        )