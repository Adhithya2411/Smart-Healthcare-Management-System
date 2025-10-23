import random
from datetime import timedelta
from django.utils import timezone
from django.core.management.base import BaseCommand
from healthcare_app.models import (
    User, DoctorProfile, PatientProfile, TimeSlot, Appointment,
    HelpRequest, Prescription
)

class Command(BaseCommand):
    help = 'Seeds the database with a large, high-profile, and realistic dataset.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('--- Starting High-Profile Database Seeding ---'))

        # 1. Cleanup Old Activity Data for a clean slate
        self.stdout.write('Step 1: Deleting all existing non-admin activity...')
        Appointment.objects.all().delete()
        TimeSlot.objects.all().delete()
        HelpRequest.objects.all().delete()
        Prescription.objects.all().delete()

        # 2. Get all sample users
        patients = list(PatientProfile.objects.all())
        doctors = list(DoctorProfile.objects.all())

        if not patients or not doctors:
            self.stdout.write(self.style.ERROR('Error: No sample patients or doctors found. Please run load_patients and load_doctors first.'))
            return
        self.stdout.write(f'Found {len(patients)} patients and {len(doctors)} doctors.')

        # 3. Help Request Scenarios
        self.stdout.write('Step 2: Seeding Help Request scenarios...')
        help_requests_data = [
            {'patient_username': 'alicew', 'specialty': 'General Medicine', 'status': 'Pending', 'desc': "Persistent dry cough and mild fever for three days. Standard flu symptoms but want to be sure."},
            {'patient_username': 'bobj', 'specialty': 'Orthopedics', 'status': 'Pending', 'desc': "Sudden, sharp pain in my left knee after going for a run yesterday. Swelling is minor."},
            {'patient_username': 'charlieb', 'specialty': 'Cardiology', 'status': 'In Progress', 'doctor_username': 'dr.chen', 'desc': "Experiencing occasional heart palpitations, especially after consuming caffeine. Should I be concerned?"},
            
            {'patient_username': 'dianak', 'specialty': 'Dermatology', 'status': 'Answered', 'doctor_username': 'dr.patel', 'desc': "A small, itchy red rash has appeared on my forearm. It looks like an insect bite but is not going away.",
             'prescription': {'diag': 'Contact Dermatitis', 'text': 'Medication: Hydrocortisone Cream 1%\nInstructions: Apply twice daily for 5-7 days. Avoid scratching.'}},
            {'patient_username': 'edwardm', 'specialty': 'General Medicine', 'status': 'Answered', 'doctor_username': 'dr.smith', 'desc': "Recurring tension headaches, especially in the afternoon. Looking for advice on management.",
             'prescription': {'diag': 'Tension Headaches', 'text': 'Medication: Ibuprofen 400mg\nInstructions: Take as needed for pain, up to 3 times a day. Ensure proper hydration and take breaks from screen time.'}},
            {'patient_username': 'fionag', 'specialty': 'Pediatrics', 'status': 'Answered', 'doctor_username': 'dr.jones', 'desc': "My 5-year-old son has a low-grade fever and a runny nose. What's the best course of action?",
             'prescription': {'diag': 'Common Cold', 'text': "Medication: Children's Paracetamol\nInstructions: Dose as per package instructions. Ensure plenty of fluids and rest. Monitor temperature."}},
            
            {'patient_username': 'georgeh', 'specialty': 'Neurology', 'status': 'Pending', 'desc': "I've been experiencing tingling sensations in my fingertips for about a week."},
        ]
        
        for data in help_requests_data:
            patient = PatientProfile.objects.get(user__username=data['patient_username'])
            request = HelpRequest.objects.create(patient=patient, specialty=data['specialty'], issue_description=data['desc'], status=data['status'])
            if data['status'] != 'Pending':
                doctor = DoctorProfile.objects.get(user__username=data['doctor_username'])
                request.doctor = doctor
                if 'prescription' in data:
                    presc_data = data['prescription']

                    Prescription.objects.create(
                        help_request=request, 
                        diagnosis=presc_data['diag'], 
                        prescription_text=presc_data['text']
                    )
                  
                request.save()
        self.stdout.write(self.style.SUCCESS(f'{len(help_requests_data)} help requests created.'))

        # 4. Appointment Scenarios
        self.stdout.write('Step 3: Seeding Appointment scenarios...')
        now = timezone.now()
        appointments_data = [
            {'patient_username': 'bobj', 'doctor_username': 'dr.williams', 'day_offset': -7, 'hour': 10, 'status': 'Completed', 'reason': 'Follow-up on knee pain.', 'notes': 'Advised RICE protocol. Patient showing improvement.'},
            {'patient_username': 'charlieb', 'doctor_username': 'dr.chen', 'day_offset': -5, 'hour': 14, 'status': 'Completed', 'reason': 'Annual cardiology checkup.', 'notes': 'ECG normal. Blood pressure slightly elevated. Recommended diet changes.'},
            {'patient_username': 'dianak', 'doctor_username': 'dr.smith', 'day_offset': -2, 'hour': 9, 'status': 'Completed', 'reason': 'General wellness check.', 'notes': 'Patient is in good health. No issues to report.'},
            {'patient_username': 'ivans', 'doctor_username': 'dr.davis', 'day_offset': 0, 'hour': now.hour, 'status': 'Booked', 'reason': 'Consultation for recurring migraines.', 'notes': ''},
            {'patient_username': 'alicew', 'doctor_username': 'dr.smith', 'day_offset': 1, 'hour': 11, 'status': 'Booked', 'reason': 'Discuss recent blood test results.', 'notes': ''},
            {'patient_username': 'fionag', 'doctor_username': 'dr.jones', 'day_offset': 2, 'hour': 9.5, 'status': 'Booked', 'reason': 'Vaccination appointment for my child.', 'notes': ''},
            {'patient_username': 'georgeh', 'doctor_username': 'dr.thomas', 'day_offset': 3, 'hour': 16, 'status': 'Booked', 'reason': 'Initial consultation for nerve tingling.', 'notes': ''},
        ]

        for data in appointments_data:
            patient = PatientProfile.objects.get(user__username=data['patient_username'])
            doctor = DoctorProfile.objects.get(user__username=data['doctor_username'])
            date = now.date() + timedelta(days=data['day_offset'])
            start_time = timezone.make_aware(timezone.datetime.combine(date, timezone.datetime.min.time()) + timedelta(hours=data['hour']))
            end_time = start_time + timedelta(minutes=30)
            
            slot = TimeSlot.objects.create(doctor=doctor, start_time=start_time, end_time=end_time, is_booked=True)
            Appointment.objects.create(patient=patient, timeslot=slot, reason=data['reason'], status=data['status'], notes=data['notes'])
        self.stdout.write(self.style.SUCCESS(f'{len(appointments_data)} specific appointments created.'))

        # 5. Create some extra available slots for booking
        self.stdout.write('Step 4: Creating extra available time slots for booking...')
        all_doctors = list(DoctorProfile.objects.all())
        for i in range(15):
            doctor = random.choice(all_doctors)
            day_offset = random.randint(1, 5)
            hour = random.choice([9, 10, 11, 14, 15, 16])
            date = now.date() + timedelta(days=day_offset)
            start_time = timezone.make_aware(timezone.datetime.combine(date, timezone.datetime.min.time()) + timedelta(hours=hour))
            end_time = start_time + timedelta(minutes=30)
            if not TimeSlot.objects.filter(doctor=doctor, start_time=start_time).exists():
                TimeSlot.objects.create(doctor=doctor, start_time=start_time, end_time=end_time)

        self.stdout.write(self.style.SUCCESS('--- High-Profile Seeding Complete! ---'))