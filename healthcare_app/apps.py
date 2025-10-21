from django.apps import AppConfig

class HealthcareAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'healthcare_app'
    
    def ready(self):
        # This imports the signals so they are connected when the app starts
        import healthcare_app.signals