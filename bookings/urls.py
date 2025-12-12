from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('calendar/', views.calendar_view, name='calendar'),
    path('api/events/', views.booking_events, name='booking_events'),
    path('create/', views.create_booking, name='create_booking'),
    path('approve/<int:booking_id>/', views.approve_booking, name='approve_booking'),
    path('reject/<int:booking_id>/', views.reject_booking, name='reject_booking'),
    path('request-deroga/<int:booking_id>/', views.request_deroga_view, name='request_deroga'),
    path('modify/<int:booking_id>/', views.modify_booking, name='modify_booking'),
]
