# In healthcare_app/admin.py

from django.contrib import admin
from .models import (
    User, DoctorProfile, PatientProfile, 
    HelpRequest, Prescription, PatientMedicalHistory,
    Symptom, SymptomOption, Suggestion 
)

# Register your models here.
admin.site.register(User)
admin.site.register(DoctorProfile)
admin.site.register(PatientProfile)
admin.site.register(HelpRequest)
admin.site.register(Prescription)
admin.site.register(PatientMedicalHistory)
admin.site.register(Symptom)         
admin.site.register(SymptomOption)      
admin.site.register(Suggestion)