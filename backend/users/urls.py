"""
URL routing for authentication and user management.

Maps API endpoints to views for registration, email verification,
login, password reset, and profile management.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    RegisterStudentView,
    RegisterFacultyView,
    VerifyEmailView,
    ResendOTPView,
    LoginView,
    LogoutView,
    PasswordResetRequestView,
    PasswordResetView,
    ProfileView,
    StudentProfileView,
    FacultyProfileView,
)

# Create router for viewset actions
router = DefaultRouter()

# Authentication endpoints (using 'create' actions)
router.register(r'register/student', RegisterStudentView, basename='register-student')
router.register(r'register/faculty', RegisterFacultyView, basename='register-faculty')
router.register(r'verify-email', VerifyEmailView, basename='verify-email')
router.register(r'resend-otp', ResendOTPView, basename='resend-otp')
router.register(r'login', LoginView, basename='login')
router.register(r'logout', LogoutView, basename='logout')
router.register(r'password-reset-request', PasswordResetRequestView, basename='password-reset-request')
router.register(r'password-reset', PasswordResetView, basename='password-reset')

# Profile endpoints
router.register(r'profile', ProfileView, basename='profile')
router.register(r'profile/student', StudentProfileView, basename='student-profile')
router.register(r'profile/faculty', FacultyProfileView, basename='faculty-profile')

app_name = 'auth'

urlpatterns = [
    path(
        'profile/faculty/',
        FacultyProfileView.as_view({'get': 'retrieve', 'patch': 'partial_update'}),
        name='faculty-profile-preferences',
    ),
    path('', include(router.urls)),
]
