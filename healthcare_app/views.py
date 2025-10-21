# In healthcare_app/views.py

from django.conf import settings
from django.shortcuts import render, redirect,get_object_or_404
from django.contrib import messages
from .forms import SignUpForm,PrescriptionForm,ProfilePictureUpdateForm
from django.contrib.auth.decorators import login_required # For basic login check
from .decorators import role_required # Our custom role checker
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from .forms import (SignUpForm, LoginForm,HelpRequestForm,PatientProfileUpdateForm,
                     DoctorProfileUpdateForm,TimeSlotForm,AppointmentNotesForm, MedicalHistoryForm,
                     ScheduleGenerationForm,AppointmentBookingForm)
from .models import (User,HelpRequest,Prescription,Symptom, SymptomOption, 
                     Suggestion,PatientMedicalHistory,TimeSlot,DoctorProfile,Appointment,Notification)
from django.db.models import Count
from django.db.models.functions import TruncDate
from datetime import date,timedelta,datetime
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
    now = timezone.localtime() # Use localtime for consistency

    # Fetch upcoming appointments
    upcoming_appointments = Appointment.objects.filter(
        timeslot__doctor=doctor_profile, 
        timeslot__start_time__gte=now.replace(hour=0, minute=0, second=0), # Get all from today
        status='Booked'
    ).order_by('timeslot__start_time')

    # --- THE ULTIMATE DEBUG BLOCK ---
    print("\n" + "="*50)
    print("          DOCTOR DASHBOARD DEBUG          ")
    print("="*50)
    print(f"Current Local Time ('now'): {now}")
    print(f"Found {upcoming_appointments.count()} upcoming appointment(s) for today.")
    print("-"*50)

    for appt in upcoming_appointments:
        start_time = appt.timeslot.start_time
        end_time = appt.timeslot.end_time

        # Perform the exact same comparisons as the template
        is_after_start = start_time <= now
        is_before_end = now <= end_time

        print(f"Appointment ID: {appt.id}")
        print(f"  - Start Time: {start_time}")
        print(f"  - End Time:   {end_time}")
        print(f"  - Check 1 (start_time <= now): {is_after_start}")
        print(f"  - Check 2 (now <= end_time):   {is_before_end}")
        print(f"  - FINAL RESULT (Both must be True): {is_after_start and is_before_end}")
        print("-"*50)

    print("="*50 + "\n")
    # --- END DEBUG BLOCK ---

    # The rest of your view is the same
    pending_requests = HelpRequest.objects.filter(status='Pending', specialty=doctor_profile.specialty).order_by('requested_at')
    active_requests = HelpRequest.objects.filter(doctor=doctor_profile, status='In Progress').order_by('requested_at')
    answered_requests = HelpRequest.objects.filter(doctor=doctor_profile, status='Answered').order_by('-prescription__prescribed_at')

    context = {
        'pending_requests': pending_requests,
        'active_requests': active_requests,
        'answered_requests': answered_requests,
        'pending_count': pending_requests.count(),
        'active_count': active_requests.count(),
        'answered_by_me_count': answered_requests.count(),
        'upcoming_appointments': upcoming_appointments,
        'now': now
    }
    return render(request, 'doctor_dashboard.html', context)

@login_required
@role_required(allowed_roles=['patient'])
def patient_dashboard(request):
    patient_profile = request.user.patientprofile
    now = timezone.localtime() # Use localtime for consistency

    # Fetch upcoming appointments
    upcoming_appointments = Appointment.objects.filter(
        patient=patient_profile,
        timeslot__start_time__gte=now.replace(hour=0, minute=0, second=0),
        status='Booked'
    ).order_by('timeslot__start_time')

    # --- DEBUG BLOCK FOR PATIENT (You can remove this later) ---
    print("\n" + "="*50)
    print("         PATIENT DASHBOARD DEBUG         ")
    print("="*50)
    print(f"Current Local Time ('now'): {now}")
    print(f"Found {upcoming_appointments.count()} upcoming appointment(s) for this patient.")
    print("-"*50)
    for appt in upcoming_appointments:
        start_time = appt.timeslot.start_time
        end_time = appt.timeslot.end_time
        is_after_start = start_time <= now
        is_before_end = now <= end_time
        print(f"Appointment ID: {appt.id}, Start: {start_time}, End: {end_time}, Result: {is_after_start and is_before_end}")
    print("="*50 + "\n")
    # --- END DEBUG BLOCK ---

    # The rest of your view is the same
    if request.method == 'POST':
        form = HelpRequestForm(request.POST, request.FILES)
        if form.is_valid():
            new_request = form.save(commit=False); new_request.patient = patient_profile; new_request.save()
            messages.success(request, 'Your help request has been submitted successfully!')
            return redirect('patient_dashboard')
    else:
        form = HelpRequestForm()

    pending_count = HelpRequest.objects.filter(patient=patient_profile, status='Pending').count()
    answered_count = HelpRequest.objects.filter(patient=patient_profile, status='Answered').count()
    past_requests = HelpRequest.objects.filter(patient=patient_profile).order_by('-requested_at')
    medical_history = PatientMedicalHistory.objects.filter(patient=patient_profile).order_by('-recorded_at')

    context = {
        'form': form, 'past_requests': past_requests, 'medical_history': medical_history,
        'pending_count': pending_count, 'answered_count': answered_count,
        'upcoming_appointments': upcoming_appointments, 'now': now
    }
    return render(request, 'patient_dashboard.html', context)

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

    if 'option_id' in request.POST:
        option_id = request.POST.get('option_id')

        try:
            selected_option = SymptomOption.objects.select_related('next_symptom', 'suggestion').get(id=option_id)

            if selected_option.next_symptom:
                context['question'] = selected_option.next_symptom
            elif hasattr(selected_option, 'suggestion'):
                context['suggestion'] = selected_option.suggestion
            else:
                messages.error(request, "This path is not configured correctly.")
                return redirect('quick_help')
        except SymptomOption.DoesNotExist:
            messages.error(request, "The selected option could not be found.")
            return redirect('quick_help')
    else:
        try:
            main_symptom = Symptom.objects.get(name='main_symptom')
            context['question'] = main_symptom
        except Symptom.DoesNotExist:
            context['error'] = "The Quick Help system is not configured yet."

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
        form = ScheduleGenerationForm(request.POST)
        if form.is_valid():
            date = form.cleaned_data['date']
            start_time = form.cleaned_data['start_time']
            end_time = form.cleaned_data['end_time']

            current_slot_start_naive = datetime.combine(date, start_time)
            final_slot_end_naive = datetime.combine(date, end_time)

            current_slot_start = timezone.make_aware(current_slot_start_naive)
            final_slot_end = timezone.make_aware(final_slot_end_naive)

            while current_slot_start < final_slot_end:
                current_slot_end = current_slot_start + timedelta(minutes=30)
                if current_slot_end > final_slot_end:
                    break
                TimeSlot.objects.create(
                    doctor=doctor_profile,
                    start_time=current_slot_start,
                    end_time=current_slot_end
                )
                current_slot_start = current_slot_end

            messages.success(request, 'Your schedule has been updated with the new time slots!')
            return redirect('manage_schedule')
        else:
            messages.error(request, 'There was an error in your form submission. Please check the details.')
    else:
        form = ScheduleGenerationForm()

    
    now = timezone.localtime()
    today = now.date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    # Query 1: Get all upcoming slots for the week
    upcoming_slots = TimeSlot.objects.filter(
        doctor=doctor_profile,
        start_time__date__range=[start_of_week, end_of_week],
        start_time__gte=now  # The slot must be in the future
    ).order_by('start_time')

    # Query 2: Get all past slots for the week
    past_slots = TimeSlot.objects.filter(
        doctor=doctor_profile,
        start_time__date__range=[start_of_week, end_of_week],
        start_time__lt=now  # The slot must be in the past
    ).order_by('-start_time')

    # Update the context to send the new variables to the template
    context = {
        'form': form,
        'upcoming_slots': upcoming_slots,
        'past_slots': past_slots,
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

# In healthcare_app/views.py

@login_required
@role_required(allowed_roles=['patient'])
def doctor_schedule_view(request, doctor_id):
    doctor = get_object_or_404(DoctorProfile, user_id=doctor_id)
    today = timezone.localtime()

    # --- TEMPORARY DEBUGGING ---
    print("=============================================")
    print(f"DEBUGGING SCHEDULE for Dr. {doctor.user.username}")
    print(f"Current Time Used for Filtering: {today}")

    # Step 1: Get ALL slots for this doctor, even past or booked ones
    all_slots_for_doctor = TimeSlot.objects.filter(doctor=doctor)
    print(f"Total slots found for this doctor (any status): {all_slots_for_doctor.count()}")

    # Step 2: Print details of a few slots to check their data
    for slot in all_slots_for_doctor.order_by('start_time')[:3]: # Check the first 3
        print(f"  - Slot ID {slot.id}: Starts at {slot.start_time}, Is Booked? {slot.is_booked}")

    # Step 3: Run the actual query the page uses
    available_slots = TimeSlot.objects.filter(
        doctor=doctor,
        start_time__gte=today,
        is_booked=False
    ).order_by('start_time')
    print(f"Slots visible to patient after filtering: {available_slots.count()}")
    print("=============================================")
    # --- END DEBUGGING ---

    context = {
        'doctor': doctor,
        'available_slots': available_slots,
    }
    return render(request, 'doctor_schedule.html', context)

@login_required
@role_required(allowed_roles=['patient'])
def book_appointment_view(request, slot_id):
    timeslot = get_object_or_404(TimeSlot, id=slot_id, is_booked=False)
    patient_profile = request.user.patientprofile

    if request.method == 'POST':
        form = AppointmentBookingForm(request.POST)
        if form.is_valid():
            # Create the appointment, but don't save yet
            appointment = form.save(commit=False)
            appointment.patient = patient_profile
            appointment.timeslot = timeslot
            appointment.save()
            
            # Mark the timeslot as booked
            timeslot.is_booked = True
            timeslot.save()
            
            messages.success(request, f"Your appointment has been booked successfully!")
            return redirect('appointment_history') # Redirect to history to see the new booking
    else:
        form = AppointmentBookingForm()

    context = {
        'form': form,
        'timeslot': timeslot,
    }
    return render(request, 'book_appointment.html', context)

@login_required
@role_required(allowed_roles=['doctor'])
def appointment_detail_view(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id, timeslot__doctor=request.user.doctorprofile)
    patient_profile = appointment.patient
    now = timezone.localtime()

    # Fetch patient's history for context
    medical_history = PatientMedicalHistory.objects.filter(patient=patient_profile).order_by('-recorded_at')
    past_answered_requests = HelpRequest.objects.filter(patient=patient_profile, status='Answered').order_by('-prescription__prescribed_at')[:5]

    # Initialize both forms
    notes_form = AppointmentNotesForm(instance=appointment)
    history_form = MedicalHistoryForm()

    if request.method == 'POST':
        # Check which form was submitted using the button's 'name' attribute
        if 'notes_form' in request.POST:
            notes_form = AppointmentNotesForm(request.POST, instance=appointment)
            if notes_form.is_valid():
                consultation = notes_form.save(commit=False)
                consultation.status = 'Completed'
                consultation.save()
                messages.success(request, "Consultation notes have been saved.")
                return redirect('doctor_dashboard')
        
        elif 'history_form' in request.POST:
            history_form = MedicalHistoryForm(request.POST)
            if history_form.is_valid():
                new_history_item = history_form.save(commit=False)
                new_history_item.patient = patient_profile
                new_history_item.save()
                messages.success(request, f"'{new_history_item.condition_name}' added to patient's medical history.")
                return redirect('appointment_detail', appointment_id=appointment.id) # Redirect back to the same page

    # For a GET request, decide what to show for the notes form
    if appointment.status == 'Completed':
        notes_form = AppointmentNotesForm(instance=appointment)

    context = {
        'appointment': appointment,
        'notes_form': notes_form,
        'history_form': history_form, 
        'medical_history': medical_history,
        'past_answered_requests': past_answered_requests,
        'now': now,
    }
    return render(request, 'appointment_detail.html', context)

@login_required
@role_required(allowed_roles=['patient'])
def appointment_history_view(request):
    patient_profile = request.user.patientprofile
    
    # Fetch all appointments for the patient, both past and future
    appointments = Appointment.objects.filter(
        patient=patient_profile
    ).order_by('-timeslot__start_time') # Show most recent first

    context = {
        'appointments': appointments,
    }
    return render(request, 'appointment_history.html', context)

@login_required
def consultation_room_view(request, appointment_id):
    # Ensure the user is authorized to be in this room
    try:
        appointment = Appointment.objects.get(id=appointment_id)
        user = request.user
        is_patient = (user.role == 'patient' and appointment.patient.user == user)
        is_doctor = (user.role == 'doctor' and appointment.timeslot.doctor.user == user)
        
        if not (is_patient or is_doctor):
            messages.error(request, "You are not authorized to view this consultation.")
            return redirect('patient_dashboard' if user.role == 'patient' else 'doctor_dashboard')

    except Appointment.DoesNotExist:
        messages.error(request, "This appointment does not exist.")
        return redirect('patient_dashboard' if user.role == 'patient' else 'doctor_dashboard')

    context = {
        'appointment_id': appointment_id,
        'username': request.user.username,
        'appointment': appointment,
    }
    return render(request, 'consultation_room.html', context)

@login_required
def mark_notification_as_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    
    # Redirect to the original link stored in the notification
    return redirect(notification.link)