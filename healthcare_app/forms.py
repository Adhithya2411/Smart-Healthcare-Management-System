# In healthcare_app/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, PatientProfile, DoctorProfile

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

from django.contrib.auth.forms import AuthenticationForm

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