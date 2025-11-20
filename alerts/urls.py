from django.urls import path
from . import views

app_name = 'alerts'

urlpatterns = [
    # Alert Management
    path('', views.user_alerts, name='user-alerts'),
    path('trigger/', views.trigger_alert, name='trigger-alert'),
    path('panic/trigger/', views.trigger_panic_alert, name='trigger-panic-alert'),
    path('panic/cancel/<uuid:alert_id>/', views.cancel_panic_alert, name='cancel-panic-alert'),
    path('<uuid:alert_id>/status/', views.update_alert_status, name='update-alert-status'),
    path('<uuid:alert_id>/notifications/', views.alert_notifications, name='alert-notifications'),
    
    # Safety Network Management
    path('safety-network/', views.safety_network_members, name='safety-network-members'),
    path('safety-network/<uuid:member_id>/', views.safety_network_member_detail, name='safety-network-member-detail'),
    
    # History
    path('panic/history/', views.panic_button_history, name='panic-button-history'),
]