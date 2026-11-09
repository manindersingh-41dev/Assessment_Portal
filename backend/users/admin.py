"""
Django admin interface for user management.

Provides admin panel for managing users, profiles, OTPs, and login attempts.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, StudentProfile, FacultyProfile, EmailOTP, LoginAttempt
from .forms import CustomUserCreationForm, CustomUserChangeForm


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface for User model."""

    form = CustomUserChangeForm
    add_form = CustomUserCreationForm

    list_display = (
        'email', 'get_full_name', 'role', 'is_email_verified',
        'is_faculty_approved', 'is_active', 'created_at'
    )
    list_filter = (
        'role', 'is_email_verified', 'is_faculty_approved', 'is_active', 'created_at'
    )
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-created_at',)

    fieldsets = (
        ('Personal Info', {
            'fields': ('email', 'first_name', 'last_name', 'password')
        }),
        ('Role & Permissions', {
            'fields': ('role', 'is_email_verified', 'is_faculty_approved', 'is_active')
        }),
        ('Admin Permissions', {
            'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_login'),
            'classes': ('collapse',)
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'first_name', 'last_name', 'role',
                'password1', 'password2',
                'is_email_verified', 'is_faculty_approved', 'is_active', 'is_staff'
            ),
        }),
    )

    readonly_fields = ('created_at', 'updated_at', 'last_login')

    def get_full_name(self, obj):
        """Display user's full name."""
        return obj.get_full_name() or '(No name)'

    get_full_name.short_description = 'Full Name'


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    """Admin interface for StudentProfile model."""

    list_display = (
        'user_email', 'roll_number', 'department', 'year_of_study',
        'enrollment_date', 'created_at'
    )
    list_filter = ('department', 'year_of_study', 'created_at')
    search_fields = ('user__email', 'roll_number', 'department')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Student Information', {
            'fields': ('roll_number', 'department', 'year_of_study', 'phone_number')
        }),
        ('Timestamps', {
            'fields': ('enrollment_date', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def user_email(self, obj):
        """Display user email."""
        return obj.user.email

    user_email.short_description = 'Email'


@admin.register(FacultyProfile)
class FacultyProfileAdmin(admin.ModelAdmin):
    """Admin interface for FacultyProfile model."""

    list_display = (
        'user_email', 'employee_id', 'department', 'designation',
        'approval_status_colored', 'created_at'
    )
    list_filter = ('department', 'approval_status', 'created_at')
    search_fields = ('user__email', 'employee_id', 'department')
    readonly_fields = ('created_at', 'updated_at', 'approval_date')
    ordering = ('-created_at',)

    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Faculty Information', {
            'fields': (
                'employee_id', 'department', 'designation', 'phone_number',
                'default_assessment_is_timed',
            )
        }),
        ('Approval Status', {
            'fields': ('approval_status', 'approved_by', 'approval_date')
        }),
        ('Timestamps', {
            'fields': ('joining_date', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def user_email(self, obj):
        """Display user email."""
        return obj.user.email

    user_email.short_description = 'Email'

    def approval_status_colored(self, obj):
        """Display approval status with color badge."""
        colors = {
            'pending': '#f59e0b',
            'approved': '#10b981',
            'rejected': '#ef4444'
        }
        color = colors.get(obj.approval_status, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_approval_status_display()
        )

    approval_status_colored.short_description = 'Approval Status'


@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    """Admin interface for EmailOTP model."""

    list_display = (
        'email', 'purpose', 'is_used', 'is_expired_display',
        'created_at', 'expires_at'
    )
    list_filter = ('purpose', 'is_used', 'created_at')
    search_fields = ('email', 'otp')
    readonly_fields = ('otp', 'created_at', 'expires_at', 'used_at')
    ordering = ('-created_at',)

    fieldsets = (
        ('OTP Information', {
            'fields': ('email', 'otp', 'purpose')
        }),
        ('Status', {
            'fields': ('is_used', 'used_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'expires_at')
        }),
    )

    def is_expired_display(self, obj):
        """Display whether OTP is expired."""
        return obj.is_expired

    is_expired_display.boolean = True
    is_expired_display.short_description = 'Expired'


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    """Admin interface for LoginAttempt model."""

    list_display = (
        'email', 'ip_address', 'success_badge', 'attempted_at'
    )
    list_filter = ('success', 'attempted_at')
    search_fields = ('email', 'ip_address')
    readonly_fields = ('email', 'ip_address', 'success', 'attempted_at')
    ordering = ('-attempted_at',)

    def success_badge(self, obj):
        """Display login success with badge."""
        color = '#10b981' if obj.success else '#ef4444'
        text = 'Success' if obj.success else 'Failed'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            text
        )

    success_badge.short_description = 'Status'

    def has_add_permission(self, request):
        """Prevent manual addition of login attempts."""
        return False

    def has_change_permission(self, request, obj=None):
        """Prevent modification of login attempts."""
        return False
