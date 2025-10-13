# In healthcare_app/decorators.py

from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect

def role_required(allowed_roles=[]):
    """
    Decorator for views that checks that the user is in one of the allowed roles.
    """
    def check_role(user):
        return user.is_authenticated and user.role in allowed_roles
    
    return user_passes_test(check_role, login_url='login')