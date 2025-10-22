import json
from django.conf import settings
from django.core.management.base import BaseCommand
from healthcare_app.models import User, DoctorProfile

class Command(BaseCommand):
    help = 'Loads sample doctor data from a JSON file'

    def handle(self, *args, **kwargs):
        # Define a default, non-secure password for all sample doctors
        default_password = 'password123'

        file_path = settings.BASE_DIR / 'healthcare_app' / 'fixtures' / 'doctors.json'
        
        self.stdout.write(self.style.SUCCESS(f'Loading doctor data from {file_path}'))

        with open(file_path, 'r') as f:
            doctors_data = json.load(f)

        for data in doctors_data:
            # Check if user already exists
            if User.objects.filter(username=data['username']).exists():
                self.stdout.write(self.style.WARNING(f"User '{data['username']}' already exists. Skipping."))
                continue

            # Create the User object
            user = User.objects.create_user(
                username=data['username'],
                email=data['email'],
                password=default_password,
                first_name=data['first_name'],
                last_name=data['last_name'],
                role='doctor'
            )

            # Create the associated DoctorProfile
            DoctorProfile.objects.create(
                user=user,
                specialty=data['specialty']
            )

            self.stdout.write(self.style.SUCCESS(f"Successfully created doctor: {data['username']}"))

        self.stdout.write(self.style.SUCCESS('\nFinished loading sample doctors.'))