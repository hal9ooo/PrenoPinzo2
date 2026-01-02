from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('calendar/', views.calendar_view, name='calendar'),
    path('statistics/', views.statistics_view, name='statistics'),
    path('chat/', views.chat_view, name='chat'),
    path('api/chat/unread/', views.unread_chat_count, name='unread_chat_count'),
    path('help/', views.help_view, name='help'),
    path('profile/', views.profile_view, name='profile'),
    path('utilities/', views.utilities_view, name='utilities'),
    path('api/events/', views.booking_events, name='booking_events'),
    path('api/holidays/', views.holiday_events, name='holiday_events'),
    path('export/ical/', views.export_ical, name='export_ical'),
    path('create/', views.create_booking, name='create_booking'),
    path('approve/<int:booking_id>/', views.approve_booking, name='approve_booking'),
    path('reject/<int:booking_id>/', views.reject_booking, name='reject_booking'),
    path('request-deroga/<int:booking_id>/', views.request_deroga_view, name='request_deroga'),
    path('modify/<int:booking_id>/', views.modify_booking, name='modify_booking'),
    path('delete/<int:booking_id>/', views.delete_booking, name='delete_booking'),
    path('update-dates/<int:booking_id>/', views.update_booking_dates, name='update_booking_dates'),
    # Home Assistant Integration
    path('api/thermostat/status/', views.get_thermostat_status, name='thermostat_status'),
    path('api/thermostat/set-temp/', views.set_thermostat_temp, name='thermostat_set_temp'),
    path('api/thermostat/set-preset/', views.set_thermostat_preset, name='thermostat_set_preset'),
    path('api/thermostat/schedule-options/', views.get_schedule_options, name='schedule_options'),
    path('api/thermostat/set-schedule/', views.set_schedule, name='set_schedule'),
    
    # Password Change
    path('password_change/', auth_views.PasswordChangeView.as_view(template_name='registration/password_change_form.html'), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='registration/password_change_done.html'), name='password_change_done'),
]
