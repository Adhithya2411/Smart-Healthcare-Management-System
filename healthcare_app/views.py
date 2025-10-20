# In healthcare_app/views.py

from django.shortcuts import render, redirect,get_object_or_404
from django.contrib import messages
from .forms import SignUpForm,PrescriptionForm,ProfilePictureUpdateForm
from django.contrib.auth.decorators import login_required # For basic login check
from .decorators import role_required # Our custom role checker
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from .forms import SignUpForm, LoginForm,HelpRequestForm,PatientProfileUpdateForm, DoctorProfileUpdateForm,TimeSlotForm
from .models import (User,HelpRequest,Prescription,Symptom, SymptomOption, 
                     Suggestion,PatientMedicalHistory,TimeSlot,DoctorProfile,Appointment)
from django.db.models import Count
from django.db.models.functions import TruncDate
from datetime import date,timedelta
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

    # Fetch pending requests that match this doctor's specialty
    pending_requests = HelpRequest.objects.filter(
        status='Pending',
        specialty=doctor_profile.specialty
    ).order_by('requested_at')

    # --- NEW: Fetch requests this doctor has claimed ---
    active_requests = HelpRequest.objects.filter(
        doctor=doctor_profile,
        status='In Progress'
    ).order_by('requested_at')

    # Fetch requests this doctor has already answered
    answered_requests = HelpRequest.objects.filter(
        doctor=doctor_profile, 
        status='Answered'
    ).order_by('-prescription__prescribed_at')

    upcoming_appointments = Appointment.objects.filter(
        timeslot__doctor=doctor_profile,
        timeslot__start_time__gte=timezone.now()
    ).order_by('timeslot__start_time')
    # --- Update the context ---
    context = {
        'pending_requests': pending_requests,
        'active_requests': active_requests,
        'answered_requests': answered_requests,
        'pending_count': pending_requests.count(),
        'active_count': active_requests.count(),
        'answered_by_me_count': answered_requests.count(),
        'upcoming_appointments': upcoming_appointments,
    }
    return render(request, 'doctor_dashboard.html', context)

@login_required
@role_required(allowed_roles=['patient'])
def patient_dashboard(request):
    patient_profile = request.user.patientprofile

    # Handle the form submission (This part is the same)
    if request.method == 'POST':
        form = HelpRequestForm(request.POST, request.FILES)
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

    upcoming_appointments = Appointment.objects.filter(
        patient=patient_profile,
        timeslot__start_time__gte=timezone.now()
    ).order_by('timeslot__start_time')

    context = {
        'form': form,
        'past_requests': past_requests,
        'medical_history': medical_history,
        'pending_count': pending_count,
        'answered_count': answered_count,
        'upcoming_appointments': upcoming_appointments,
    }
    return render(request, 'patient_dashboard.html', context)
# In healthcare_app/views.py

# In healthcare_app/views.py

# In healthcare_app/views.py

@login_required
@role_required(allowed_roles=['doctor'])
def request_detail_view(request, request_id):
    help_request = get_object_or_404(HelpRequest, id=request_id)
    patient_profile = help_request.patient

    medical_history = PatientMedicalHistory.objects.filter(
        patient=patient_profile
    ).order_by('-recorded_at')
    
    past_answered_requests = HelpRequest.objects.filter(
        patient=patient_profile, 
        status='Answered'
    ).exclude(id=request_id).order_by('-prescription__prescribed_at')[:5]

    context = {
        'help_request': help_request,
        'medical_history': medical_history,
        'past_answered_requests': past_answered_requests,
    }
    form = None
    
    # Show the form if the request is waiting in the queue OR if it's assigned to you.
    if help_request.status in ['Pending', 'In Progress']:
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
    else: # This will now only run for "Answered" or "Closed" requests
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

@login_required
def profile_picture_upload_view(request):
    # Get the correct profile based on the user's role
    if hasattr(request.user, 'patientprofile'):
        profile_instance = request.user.patientprofile
    elif hasattr(request.user, 'doctorprofile'):
        profile_instance = request.user.doctorprofile
    else:
        messages.error(request, 'No valid profile found to update.')
        return redirect('profile')

    if request.method == 'POST':
        # request.FILES is used for file uploads
        form = ProfilePictureUpdateForm(request.POST, request.FILES, instance=profile_instance)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile picture has been updated!')
            return redirect('profile')
    else:
        form = ProfilePictureUpdateForm(instance=profile_instance)

    context = {'form': form}
    return render(request, 'profile_picture_upload.html', context)

login_required
@role_required(allowed_roles=['doctor'])
def assign_request_view(request, request_id):
    # Find the request, ensuring it's still pending
    help_request = get_object_or_404(HelpRequest, id=request_id, status='Pending')
    
    if request.method == 'POST':
        # Assign the current doctor and update the status
        help_request.doctor = request.user.doctorprofile
        help_request.status = 'In Progress'
        help_request.save()
        messages.success(request, f"Request from '{help_request.patient.user.username}' has been assigned to you.")
        return redirect('doctor_dashboard')

    # If it's a GET request, just redirect away
    return redirect('doctor_dashboard')

@login_required
@role_required(allowed_roles=['doctor'])
def manage_schedule_view(request):
    doctor_profile = request.user.doctorprofile
    
    if request.method == 'POST':
        form = TimeSlotForm(request.POST)
        if form.is_valid():
            timeslot = form.save(commit=False)
            timeslot.doctor = doctor_profile
            timeslot.save()
            messages.success(request, 'New time slot added successfully!')
            return redirect('manage_schedule')
    else:
        form = TimeSlotForm()

    # Get today's date and the start/end of the current week
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    # Fetch all timeslots for the current week
    timeslots = TimeSlot.objects.filter(
        doctor=doctor_profile,
        start_time__date__range=[start_of_week, end_of_week]
    ).order_by('start_time')

    context = {
        'form': form,
        'timeslots': timeslots,
        'current_week': f"{start_of_week.strftime('%b %d')} - {end_of_week.strftime('%b %d, %Y')}"
    }
    return render(request, 'manage_schedule.html', context)

@login_required
@role_required(allowed_roles=['patient'])
def doctor_list_view(request):
    doctors = DoctorProfile.objects.all()
    context = {
        'doctors': doctors,
    }
    return render(request, 'doctor_list.html', context)

@login_required
@role_required(allowed_roles=['patient'])
def doctor_schedule_view(request, doctor_id):
    doctor = get_object_or_404(DoctorProfile, user_id=doctor_id)

    # Fetch all available (not booked) timeslots for this doctor from today onwards
    today = timezone.now()
    available_slots = TimeSlot.objects.filter(
        doctor=doctor,
        start_time__gte=today,
        is_booked=False
    ).order_by('start_time')

    context = {
        'doctor': doctor,
        'available_slots': available_slots,
    }
    return render(request, 'doctor_schedule.html', context)

@login_required
@role_required(allowed_roles=['patient'])
def book_appointment_view(request, slot_id):
    # Ensure the request is a POST request for security
    if request.method == 'POST':
        # Find the timeslot, ensuring it is not already booked
        timeslot = get_object_or_404(TimeSlot, id=slot_id, is_booked=False)
        patient_profile = request.user.patientprofile
        
        # Create the new appointment
        Appointment.objects.create(patient=patient_profile, timeslot=timeslot)
        
        # Mark the timeslot as booked
        timeslot.is_booked = True
        timeslot.save()
        
        messages.success(request, f"Your appointment with Dr. {timeslot.doctor.user.get_full_name()} has been booked successfully!")
        return redirect('patient_dashboard')

    # If it's a GET request, just redirect away
    return redirect('doctor_list')