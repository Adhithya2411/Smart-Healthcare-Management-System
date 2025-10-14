# In healthcare_app/views.py

from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import SignUpForm
from django.contrib.auth.decorators import login_required # For basic login check
from .decorators import role_required # Our custom role checker
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from .forms import SignUpForm, LoginForm,HelpRequestForm
from .models import HelpRequest 

def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now log in.')
            # After successful signup, redirect to the login page
            # We will create the 'login' URL name in the next steps
            return redirect('login') 
        else: # This block runs when the form is NOT valid
            print("--- SIGNUP FORM ERRORS ---") # Add this line
            print(form.errors) 
    else:
        form = SignUpForm()
    
    return render(request, 'signup.html', {'form': form})

class CustomLoginView(LoginView):
    form_class = LoginForm
    template_name = 'login.html'

    def get_success_url(self):
        user = self.request.user
        
        if user.is_authenticated:
            if user.role == 'admin':
                # We will create the 'admin_dashboard' URL name later
                return reverse_lazy('admin_dashboard') 
            elif user.role == 'doctor':
                # We will create the 'doctor_dashboard' URL name later
                return reverse_lazy('doctor_dashboard')
            else: # Patient
                # We will create the 'patient_dashboard' URL name later
                return reverse_lazy('patient_dashboard')
        
        # Fallback for any other case
        return reverse_lazy('login')
    

@login_required
@role_required(allowed_roles=['admin'])
def admin_dashboard(request):
    return render(request, 'admin_dashboard.html')

@login_required
@role_required(allowed_roles=['doctor'])
def doctor_dashboard(request):
    # Fetch all help requests that have the status 'Pending'
    # Order them by the oldest first, to create a queue
    pending_requests = HelpRequest.objects.filter(status='Pending').order_by('requested_at')
    
    context = {
        'pending_requests': pending_requests
    }
    return render(request, 'doctor_dashboard.html', context)

@login_required
@role_required(allowed_roles=['patient'])
def patient_dashboard(request):
    # Get the profile of the currently logged-in patient
    patient_profile = request.user.patientprofile

    # Handle the form submission (when the user clicks "Submit Request")
    if request.method == 'POST':
        form = HelpRequestForm(request.POST)
        if form.is_valid():
            # Create a model instance but don't save to the DB yet
            new_request = form.save(commit=False)
            # Assign the current patient to the request before saving
            new_request.patient = patient_profile
            new_request.save()
            
            messages.success(request, 'Your help request has been submitted successfully!')
            return redirect('patient_dashboard')
    else:
        # Handle the initial page load by creating a blank form
        form = HelpRequestForm()

    # Get all past requests for this patient to display in a list
    past_requests = HelpRequest.objects.filter(patient=patient_profile).order_by('-requested_at')
    
    context = {
        'form': form,
        'past_requests': past_requests
    }
    return render(request, 'patient_dashboard.html', context)