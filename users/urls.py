from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

app_name = 'users'

urlpatterns = [
    # Authentication
    path('register/', views.register_user, name='register'),
    path('login/', views.login_user, name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Profile Management
    path('profile/', views.user_profile, name='user-profile'),
    path('safety-network/', views.update_safety_network, name='safety-network'),
    path('medical-info/', views.update_medical_info, name='medical-info'),
    
    # Emergency Contacts
    path('emergency-contacts/', views.emergency_contacts, name='emergency-contacts'),
    path('emergency-contacts/<uuid:contact_id>/', views.emergency_contact_detail, name='emergency-contact-detail'),
]