# In healthcare_app/views.py

from django.shortcuts import render, redirect,get_object_or_404
from django.contrib import messages
from .forms import SignUpForm,PrescriptionForm
from django.contrib.auth.decorators import login_required # For basic login check
from .decorators import role_required # Our custom role checker
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from .forms import SignUpForm, LoginForm,HelpRequestForm,PatientProfileUpdateForm, DoctorProfileUpdateForm
from .models import User,HelpRequest,Prescription,Symptom, SymptomOption, Suggestion
from django.db.models import Count
from django.db.models.functions import TruncDate
from datetime import timedelta
from django.utils import timezone
import json

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
    # Stat card counts (same as before)
    patient_count = User.objects.filter(role='patient').count()
    doctor_count = User.objects.filter(role='doctor').count()
    pending_requests_count = HelpRequest.objects.filter(status='Pending').count()
    completed_requests_count = HelpRequest.objects.filter(status='Answered').count()

    # --- New Logic for Chart Data ---
    # Calculate the date 7 days ago
    seven_days_ago = timezone.now().date() - timedelta(days=6)
    
    # Query for help requests in the last 7 days, grouped by day
    requests_per_day = (
        HelpRequest.objects.filter(requested_at__date__gte=seven_days_ago)
        .annotate(date=TruncDate('requested_at'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )

    # Create a dictionary to hold data for all last 7 days, initialized to 0
    requests_data = { (seven_days_ago + timedelta(days=i)): 0 for i in range(7) }
    
    # Populate the dictionary with actual counts from the query
    for entry in requests_per_day:
        requests_data[entry['date']] = entry['count']

    # Prepare labels and data for Chart.js
    chart_labels = [date.strftime('%b %d') for date in requests_data.keys()]
    chart_data = list(requests_data.values())

    context = {
        'patient_count': patient_count,
        'doctor_count': doctor_count,
        'pending_requests_count': pending_requests_count,
        'completed_requests_count': completed_requests_count,
        # Add the chart data to the context, converting it to JSON
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
    }
    return render(request, 'admin_dashboard.html', context)

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

@login_required
@role_required(allowed_roles=['patient'])
def quick_help_view(request):
    context = {}
    
    # If the user has selected an option
    if request.method == 'POST':
        option_id = request.POST.get('option_id')
        try:
            # Find the suggestion linked to the chosen option
            selected_option = SymptomOption.objects.get(id=option_id)
            suggestion = selected_option.suggestion
            context['suggestion'] = suggestion
        except (SymptomOption.DoesNotExist, Suggestion.DoesNotExist):
            messages.error(request, "Sorry, a suggestion for that option could not be found.")
            return redirect('quick_help')

    # If it's the first visit to the page
    else:
        try:
            # Fetch the first question we want to ask
            main_symptom = Symptom.objects.get(name='main_symptom')
            context['question'] = main_symptom
        except Symptom.DoesNotExist:
            context['error'] = "The Quick Help system is not configured yet. Please check back later."
            
    return render(request, 'quick_help.html', context)

@login_required
def profile_view(request):
    # The view will pass the request.user object to the template automatically.
    return render(request, 'profile.html')


def index_view(request):
    # If the user is already logged in, redirect them to their dashboard
    if request.user.is_authenticated:
        if request.user.role == 'admin':
            return redirect('admin_dashboard')
        elif request.user.role == 'doctor':
            return redirect('doctor_dashboard')
        else:
            return redirect('patient_dashboard')

    # If they are not logged in, show the landing page
    return render(request, 'index.html')

@login_required
def profile_edit_view(request):
    if request.user.role == 'patient':
        profile_instance = request.user.patientprofile
        form_class = PatientProfileUpdateForm
    elif request.user.role == 'doctor':
        profile_instance = request.user.doctorprofile
        form_class = DoctorProfileUpdateForm
    else: # Admin or other roles
        messages.error(request, 'Only Patients and Doctors can edit their profiles.')
        return redirect('profile')

    if request.method == 'POST':
        form = form_class(request.POST, instance=profile_instance)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('profile')
    else:
        form = form_class(instance=profile_instance)

    context = {'form': form}
    return render(request, 'profile_edit.html', context)