# In healthcare_app/urls.py (the new file)

from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView
from .views import (
    signup_view, 
    CustomLoginView,
    admin_dashboard,
    doctor_dashboard,
    patient_dashboard
)

urlpatterns = [
    path('signup/', views.signup_view, name='signup'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),


    # Dashboard URLs
    path('dashboard/admin/', admin_dashboard, name='admin_dashboard'),
    path('dashboard/doctor/', doctor_dashboard, name='doctor_dashboard'),
    path('dashboard/patient/', patient_dashboard, name='patient_dashboard'),
]