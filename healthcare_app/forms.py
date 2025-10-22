# In healthcare_app/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import AuthenticationForm
from .models import User, PatientProfile, DoctorProfile,HelpRequest,Prescription,TimeSlot,Appointment,PatientMedicalHistory
from datetime import datetime

class SignUpForm(UserCreationForm):

    ROLE_CHOICES = (
        ('patient', 'I am a Patient'),
    )

    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        required=True,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        placeholders = {
            'username': 'Username',
            'email': 'Email Address',
            'first_name': 'First Name',
            'last_name': 'Last Name',
        }

        for field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.RadioSelect):
                field.widget.attrs.update({'class': 'form-control'})
            
            if field_name in placeholders:
                field.widget.attrs.update({'placeholder': placeholders[field_name]})
                field.label = ''
            
            # Add placeholders for the password fields
            if field_name == 'password1':
                field.widget.attrs.update({'placeholder': 'Password'})
            if field_name == 'password2':
                field.widget.attrs.update({'placeholder': 'Confirm Password'})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'patient'
        if commit:
            user.save()
            PatientProfile.objects.create(user=user)
        return user



class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add placeholders and Bootstrap classes to the fields
        self.fields['username'].widget.attrs.update(
            {'class': 'form-control', 'placeholder': 'Username'}
        )
        self.fields['password'].widget.attrs.update(
            {'class': 'form-control', 'placeholder': 'Password'}
        )

class HelpRequestForm(forms.ModelForm):
    class Meta:
        model = HelpRequest
        # We only want the patient to fill out the description. The rest is automatic.
        fields = ['specialty', 'issue_description', 'attachment']
        widgets = {
            'specialty': forms.Select(attrs={'class': 'form-select'}),
            'issue_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Please describe your medical issue in detail...'
            }),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'specialty': 'Select a Medical Specialty',
            'issue_description': 'Your Medical Concern',
            'attachment': 'Add an Attachment (Optional)',
        }

class PrescriptionForm(forms.ModelForm):
    class Meta:
        model = Prescription
        fields = ['diagnosis', 'prescription_text']
        widgets = {
            'diagnosis': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'e.g., Viral Pharyngitis'
            }),
            'prescription_text': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4,
                'placeholder': 'e.g., Advil 200mg twice a day for 3 days...'
            }),
        }
        labels = {
            'diagnosis': 'Diagnosis',
            'prescription_text': 'Prescription & Advice'
        }

class PatientProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = PatientProfile
        fields = ['age', 'gender', 'contact']
        widgets = {
            'age': forms.NumberInput(attrs={'class': 'form-control'}),
            'gender': forms.TextInput(attrs={'class': 'form-control'}),
            'contact': forms.TextInput(attrs={'class': 'form-control'}),
        }

class DoctorProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = DoctorProfile
        fields = ['specialty', 'years_of_experience']
        widgets = {
            'specialty': forms.TextInput(attrs={'class': 'form-control'}),
            'years_of_experience': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class ProfilePictureUpdateForm(forms.ModelForm):
    class Meta:
        # We can use either profile model, as the field is the same.
        # This form will be used to update the 'profile_picture' field only.
        model = PatientProfile 
        fields = ['profile_picture']

class TimeSlotForm(forms.ModelForm):
    class Meta:
        model = TimeSlot
        fields = ['start_time', 'end_time']
        widgets = {
            # Use HTML5 datetime-local input for a nice user experience
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        }

class AppointmentNotesForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['diagnosis', 'notes']
        widgets = {
            'diagnosis': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Common Cold'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Advised patient to rest and stay hydrated...'}),
        }

class ScheduleGenerationForm(forms.Form):
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    start_time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}))
    end_time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}))

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")

        if start_time and end_time:
            if end_time <= start_time:
                # This error will now be displayed to the user
                raise forms.ValidationError("End time must be after start time.")
        return cleaned_data

class AppointmentBookingForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['reason']
        widgets = {
            'reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Please provide a brief reason for your visit...'
            })
        }

class MedicalHistoryForm(forms.ModelForm):
    class Meta:
        model = PatientMedicalHistory
        fields = ['condition_name', 'status']
        widgets = {
            'condition_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Hypertension, Asthma'}),
            'status': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Chronic, Recovered'}),
        }
        labels = {
            'condition_name': 'Condition',
            'status': 'Current Status',
        }

class DoctorCreationForm(UserCreationForm):
    specialty = forms.ChoiceField(choices=DoctorProfile.SPECIALTY_CHOICES, required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')
        
    # This method adds the Bootstrap classes to each form field
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'doctor'
        if commit:
            user.save()
            DoctorProfile.objects.create(
                user=user,
                specialty=self.cleaned_data.get('specialty')
            )
        return user