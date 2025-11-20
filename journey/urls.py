from django.urls import path
from . import views

app_name = 'journey'

urlpatterns = [
    # Journey Management
    path('', views.journey_list, name='journey-list'),
    path('active/', views.active_journey, name='active-journey'),
    path('<uuid:journey_id>/', views.journey_detail, name='journey-detail'),
    path('<uuid:journey_id>/start/', views.start_journey, name='start-journey'),
    path('<uuid:journey_id>/complete/', views.complete_journey, name='complete-journey'),
    path('<uuid:journey_id>/alerts/', views.journey_alerts, name='journey-alerts'),
    
    # Location Tracking
    path('location/update/', views.update_location, name='update-location'),
    
    # Group Journeys
    path('group/create/', views.create_group_journey, name='create-group-journey'),
    path('group/join/', views.join_group_journey, name='join-group-journey'),
    path('<uuid:journey_id>/passengers/', views.group_journey_passengers, name='group-journey-passengers'),
]