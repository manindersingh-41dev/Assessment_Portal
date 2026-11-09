"""
Custom forms for UserAdmin.

Handles user creation and modification in the Django admin when username is replaced by email.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User


class CustomUserCreationForm(UserCreationForm):
    """Form for creating a new User in Django admin."""

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'role', 'is_email_verified', 'is_faculty_approved', 'is_active', 'is_staff')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with that email already exists.")
        return email


class CustomUserChangeForm(UserChangeForm):
    """Form for modifying an existing User in Django admin."""

    class Meta:
        model = User
        fields = '__all__'
