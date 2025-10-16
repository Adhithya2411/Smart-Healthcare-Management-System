# In healthcare_app/views.py

from django.shortcuts import render, redirect,get_object_or_404
from django.contrib import messages
from .forms import SignUpForm,PrescriptionForm
from django.contrib.auth.decorators import login_required # For basic login check
from .decorators import role_required # Our custom role checker
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from .forms import SignUpForm, LoginForm,HelpRequestForm
from .models import HelpRequest,Prescription

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

# In healthcare_app/views.py

@login_required
@role_required(allowed_roles=['doctor'])
def request_detail_view(request, request_id):
    help_request = get_object_or_404(HelpRequest, id=request_id)
    
    # Initialize context and form variables
    context = {'help_request': help_request}
    form = None
    
    # Check if the request is still pending
    if help_request.status == 'Pending':
        if request.method == 'POST':
            form = PrescriptionForm(request.POST)
            if form.is_valid():
                new_prescription = form.save(commit=False)
                new_prescription.help_request = help_request
                new_prescription.save()
                
                # Update request status and assign the doctor
                help_request.status = 'Answered'
                help_request.doctor = request.user.doctorprofile
                help_request.save()
                
                messages.success(request, 'Your response has been submitted successfully!')
                return redirect('doctor_dashboard')
        else:
            # If it's a GET request for a pending item, show the blank form
            form = PrescriptionForm()
        
        # Add the form to the context only if the request is pending
        context['form'] = form
    else:
        # If the request is NOT pending, fetch the existing prescription to display it
        # The 'prescription' related name comes from the OneToOneField on the Prescription model
        existing_prescription = get_object_or_404(Prescription, help_request=help_request)
        context['prescription'] = existing_prescription

    return render(request, 'request_detail.html', context)