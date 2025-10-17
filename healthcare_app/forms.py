# In healthcare_app/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import AuthenticationForm
from .models import User, PatientProfile, DoctorProfile,HelpRequest,Prescription

class SignUpForm(UserCreationForm):
    ROLE_CHOICES = (
        ('patient', 'I am a Patient'),
        ('doctor', 'I am a Doctor'),
    )
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        required=True,
        # The widget is important for styling in the template
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}) 
    )
    
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')

    # This __init__ method is new. It's used to add CSS classes to the fields.
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        placeholders = {
            'username': 'Username',
            'email': 'Email Address',
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'password': 'Password',
            'password2': 'Confirm Password'
        }

        for field_name, placeholder_text in placeholders.items():
            if field_name in self.fields:
                field = self.fields[field_name]
                field.widget.attrs.update({
                    'class': 'form-control',
                    'placeholder': placeholder_text
                })
                # We can also remove the default labels now
                field.label = ''

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = self.cleaned_data['role']
        
        if commit:
            user.save()
            if user.role == 'patient':
                PatientProfile.objects.create(user=user)
            elif user.role == 'doctor':
                DoctorProfile.objects.create(user=user)
                
        return user
    
# In healthcare_app/forms.py
# Add this code below the SignUpForm class



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
        fields = ['issue_description']
        widgets = {
            'issue_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Please describe your medical issue in detail...'
            }),
        }
        labels = {
            'issue_description': 'Your Medical Concern'
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