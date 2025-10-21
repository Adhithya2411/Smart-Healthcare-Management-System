# In healthcare_app/models.py

from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('doctor', 'Doctor'),
        ('patient', 'Patient'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='patient')

class DoctorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name='doctorprofile')
    specialty = models.CharField(max_length=100, default="General Physician")
    years_of_experience = models.PositiveIntegerField(default=0)

    profile_picture = models.ImageField(default='images/default_avatar.png', upload_to='profile_pics/')

    def __str__(self):
        return self.user.username

class PatientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name='patientprofile')
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True)
    contact = models.CharField(max_length=15, null=True, blank=True)

    profile_picture = models.ImageField(default='images/default_avatar.png', upload_to='profile_pics/')

    def __str__(self):
        return self.user.username

class HelpRequest(models.Model):

    SPECIALTY_CHOICES = (
        ('General Medicine', 'General Medicine'),
        ('Dermatology', 'Dermatology'),
        ('Orthopedics', 'Orthopedics'),
        ('Cardiology', 'Cardiology'),
        ('Neurology', 'Neurology'),
    )

    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Answered', 'Answered'),
        ('Closed', 'Closed'),
    )
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE)
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.SET_NULL, null=True, blank=True)
    issue_description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    requested_at = models.DateTimeField(auto_now_add=True)

    specialty = models.CharField(max_length=50, choices=SPECIALTY_CHOICES, default='General Medicine')
    attachment = models.ImageField(upload_to='attachments/', null=True, blank=True)

    def __str__(self):
        return f"Request from {self.patient.user.username} - Status: {self.status}"

class Prescription(models.Model):
    help_request = models.OneToOneField(HelpRequest, on_delete=models.CASCADE)
    diagnosis = models.CharField(max_length=255)
    prescription_text = models.TextField()
    prescribed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Prescription for Request ID: {self.help_request.id}"

class PatientMedicalHistory(models.Model):
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE)
    condition_name = models.CharField(max_length=255)
    status = models.CharField(max_length=100)
    recorded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient.user.username} - {self.condition_name}"

class Symptom(models.Model):
    name = models.CharField(max_length=100, unique=True)
    question_text = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class SymptomOption(models.Model):
    symptom = models.ForeignKey(Symptom, on_delete=models.CASCADE, related_name='options')
    option_text = models.CharField(max_length=100)
    
    next_symptom = models.ForeignKey(Symptom, on_delete=models.SET_NULL, null=True, blank=True, related_name='parent_options')

    def __str__(self):
        return f"{self.symptom.name} - {self.option_text}"

class Suggestion(models.Model):

    option = models.OneToOneField(SymptomOption, on_delete=models.CASCADE, related_name='suggestion', null=True, blank=True)
    suggestion_text = models.TextField()
    is_prescription_needed = models.BooleanField(default=False)

    def __str__(self):
        if self.option:
            return f"Suggestion for {self.option.option_text}"
        return "Generic Suggestion"
    

class TimeSlot(models.Model):
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name='timeslots')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_booked = models.BooleanField(default=False)

    def __str__(self):
        return f"Slot for Dr. {self.doctor.user.username} from {self.start_time.strftime('%Y-%m-%d %H:%M')} to {self.end_time.strftime('%H:%M')}"

class Appointment(models.Model):

    STATUS_CHOICES = (
        ('Booked', 'Booked'),
        ('Completed', 'Completed'),
    )

    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='appointments')
    timeslot = models.OneToOneField(TimeSlot, on_delete=models.CASCADE, related_name='appointment')
    reason = models.TextField()

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Booked')
    diagnosis = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Appointment for {self.patient.user.username} with Dr. {self.timeslot.doctor.user.username}"
    
class ChatMessage(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message by {self.user.username} in Appointment {self.appointment.id}"