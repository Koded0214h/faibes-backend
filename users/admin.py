from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, EmergencyContact, UserSession

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['phone', 'email', 'full_name', 'is_active', 'date_joined']
    list_filter = ['is_active', 'is_staff', 'date_joined']
    search_fields = ['phone', 'email', 'full_name']
    ordering = ['-date_joined']
    
    fieldsets = (
        (None, {'fields': ('phone', 'email', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'next_of_kin_name', 'next_of_kin_phone')}),
        ('Safety Info', {'fields': ('medical_info', 'safety_network', 'safe_word', 'voice_trigger_enabled')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone', 'email', 'full_name', 'password1', 'password2'),
        }),
    )

@admin.register(EmergencyContact)
class EmergencyContactAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'user', 'relationship', 'is_primary']
    list_filter = ['is_primary', 'relationship']
    search_fields = ['name', 'phone', 'user__full_name']

@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'device_id', 'is_active', 'created_at', 'last_activity']
    list_filter = ['is_active', 'created_at']
    search_fields = ['user__full_name', 'device_id']