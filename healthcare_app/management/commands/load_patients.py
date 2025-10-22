import json
from django.conf import settings
from django.core.management.base import BaseCommand
from healthcare_app.models import User, PatientProfile

class Command(BaseCommand):
    help = 'Loads sample patient data from a JSON file'

    def handle(self, *args, **kwargs):
        
        default_password = 'password123'

        file_path = settings.BASE_DIR / 'healthcare_app' / 'fixtures' / 'patients.json'
        
        self.stdout.write(self.style.SUCCESS(f'Loading patient data from {file_path}'))

        with open(file_path, 'r') as f:
            patients_data = json.load(f)

        for data in patients_data:
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
                role='patient' # Set role to 'patient'
            )

            # Create the associated PatientProfile
            PatientProfile.objects.create(user=user)

            self.stdout.write(self.style.SUCCESS(f"Successfully created patient: {data['username']}"))

        self.stdout.write(self.style.SUCCESS('\nFinished loading sample patients.'))