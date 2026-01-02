from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, Booking

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'

class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('title', 'family_group', 'start_date', 'end_date', 'status', 'pending_with')
    list_filter = ('family_group', 'status')
    search_fields = ('title', 'user__username')
