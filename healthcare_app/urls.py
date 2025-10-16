# In healthcare_app/urls.py

from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import (
    signup_view, 
    CustomLoginView,
    admin_dashboard,
    doctor_dashboard,
    patient_dashboard,
    request_detail_view # <-- Import the new view
)

urlpatterns = [
    # Authentication URLs
    path('signup/', signup_view, name='signup'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),

    # Dashboard URLs
    path('dashboard/admin/', admin_dashboard, name='admin_dashboard'),
    path('dashboard/doctor/', doctor_dashboard, name='doctor_dashboard'),
    path('dashboard/patient/', patient_dashboard, name='patient_dashboard'),
    
    # New URL for a single request
    # The <int:request_id> part captures the ID from the URL
    path('request/<int:request_id>/', request_detail_view, name='request_detail'),
]