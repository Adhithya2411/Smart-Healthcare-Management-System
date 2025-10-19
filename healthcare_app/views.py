# In healthcare_app/views.py

from django.shortcuts import render, redirect,get_object_or_404
from django.contrib import messages
from .forms import SignUpForm,PrescriptionForm
from django.contrib.auth.decorators import login_required # For basic login check
from .decorators import role_required # Our custom role checker
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from .forms import SignUpForm, LoginForm,HelpRequestForm,PatientProfileUpdateForm, DoctorProfileUpdateForm
from .models import User,HelpRequest,Prescription,Symptom, SymptomOption, Suggestion,PatientMedicalHistory
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
    # --- 1. Data for Stat Cards ---
    patient_count = User.objects.filter(role='patient').count()
    doctor_count = User.objects.filter(role='doctor').count()
    pending_requests_count = HelpRequest.objects.filter(status='Pending').count()
    completed_requests_count = HelpRequest.objects.filter(status='Answered').count()

    # --- 2. Data for Bar Chart (Requests per Day) ---
    seven_days_ago = timezone.now().date() - timedelta(days=6)
    requests_per_day_query = (
        HelpRequest.objects.filter(requested_at__date__gte=seven_days_ago)
        .annotate(date=TruncDate('requested_at'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )
    requests_data = { (seven_days_ago + timedelta(days=i)).strftime('%b %d'): 0 for i in range(7) }
    for entry in requests_per_day_query:
        requests_data[entry['date'].strftime('%b %d')] = entry['count']
    bar_chart_labels = list(requests_data.keys())
    bar_chart_data = list(requests_data.values())

    # --- 3. Data for Pie Chart (Request Status Breakdown) ---
    pie_chart_labels = ['Pending', 'Answered']
    pie_chart_data = [pending_requests_count, completed_requests_count]

    # --- 4. Data for User Management Table ---
    # Fetch the 5 most recently joined patients and doctors
    latest_patients = User.objects.filter(role='patient').order_by('-date_joined')[:5]
    latest_doctors = User.objects.filter(role='doctor').order_by('-date_joined')[:5]

    context = {
        'patient_count': patient_count,
        'doctor_count': doctor_count,
        'pending_requests_count': pending_requests_count,
        'completed_requests_count': completed_requests_count,
        'bar_chart_labels': json.dumps(bar_chart_labels),
        'bar_chart_data': json.dumps(bar_chart_data),
        'pie_chart_labels': json.dumps(pie_chart_labels),
        'pie_chart_data': json.dumps(pie_chart_data),
        'latest_patients': latest_patients,
        'latest_doctors': latest_doctors,
    }
    return render(request, 'admin_dashboard.html', context)

@login_required
@role_required(allowed_roles=['doctor'])
def doctor_dashboard(request):
    doctor_profile = request.user.doctorprofile

    # --- 1. Data for Stat Cards ---
    # Count requests assigned to this specific doctor
    answered_by_me_count = HelpRequest.objects.filter(doctor=doctor_profile, status='Answered').count()

    # --- 2. Data for the "Pending" Table ---
    # Fetch all help requests that are not yet assigned to any doctor
    pending_requests = HelpRequest.objects.filter(status='Pending').order_by('requested_at')
    pending_count = pending_requests.count()

    # --- 3. Data for the "My History" Table ---
    # Fetch all requests this doctor has already answered
    answered_requests = HelpRequest.objects.filter(doctor=doctor_profile, status='Answered').order_by('-prescription__prescribed_at')

    context = {
        'answered_by_me_count': answered_by_me_count,
        'pending_count': pending_count,
        'pending_requests': pending_requests,
        'answered_requests': answered_requests,
    }
    return render(request, 'doctor_dashboard.html', context)
@login_required
@role_required(allowed_roles=['patient'])
def patient_dashboard(request):
    patient_profile = request.user.patientprofile

    # Handle the form submission (This part is the same)
    if request.method == 'POST':
        form = HelpRequestForm(request.POST)
        if form.is_valid():
            new_request = form.save(commit=False)
            new_request.patient = patient_profile
            new_request.save()
            messages.success(request, 'Your help request has been submitted successfully!')
            return redirect('patient_dashboard')
    else:
        form = HelpRequestForm()

    # --- 1. Data for Stat Cards ---
    pending_count = HelpRequest.objects.filter(patient=patient_profile, status='Pending').count()
    answered_count = HelpRequest.objects.filter(patient=patient_profile, status='Answered').count()

    # --- 2. Data for "Request History" ---
    past_requests = HelpRequest.objects.filter(patient=patient_profile).order_by('-requested_at')

    # --- 3. Data for "Medical History" ---
    medical_history = PatientMedicalHistory.objects.filter(patient=patient_profile).order_by('-recorded_at')

    context = {
        'form': form,
        'past_requests': past_requests,
        'medical_history': medical_history,
        'pending_count': pending_count,
        'answered_count': answered_count,
    }
    return render(request, 'patient_dashboard.html', context)
# In healthcare_app/views.py

# In healthcare_app/views.py

@login_required
@role_required(allowed_roles=['doctor'])
def request_detail_view(request, request_id):
    help_request = get_object_or_404(HelpRequest, id=request_id)
    patient_profile = help_request.patient

    # --- NEW: Fetch patient's complete history ---
    # 1. Fetch long-term medical conditions
    medical_history = PatientMedicalHistory.objects.filter(
        patient=patient_profile
    ).order_by('-recorded_at')
    
    # 2. Fetch past answered requests (excluding the current one)
    past_answered_requests = HelpRequest.objects.filter(
        patient=patient_profile, 
        status='Answered'
    ).exclude(id=request_id).order_by('-prescription__prescribed_at')[:5] # Limit to 5 recent

    # Initialize context and form variables
    context = {
        'help_request': help_request,
        'medical_history': medical_history,
        'past_answered_requests': past_answered_requests,
    }
    form = None
    
    # Check if the request is still pending
    if help_request.status == 'Pending':
        if request.method == 'POST':
            form = PrescriptionForm(request.POST)
            if form.is_valid():
                new_prescription = form.save(commit=False)
                new_prescription.help_request = help_request
                new_prescription.save()
                
                help_request.status = 'Answered'
                help_request.doctor = request.user.doctorprofile
                help_request.save()
                
                messages.success(request, 'Your response has been submitted successfully!')
                return redirect('doctor_dashboard')
        else:
            form = PrescriptionForm()
        
        context['form'] = form
    else:
        # If the request is NOT pending, fetch the existing prescription
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