"""
Models for Geeta University Coding Assessment Portal users app.

Exports:
- Base models: UUIDModel, TimeStampedModel, CreatedByModel
- User models: User, StudentProfile, FacultyProfile
- Authentication models: EmailOTP, LoginAttempt
"""

from .base import UUIDModel, TimeStampedModel, CreatedByModel  # noqa: F401
from .auth import (  # noqa: F401
    User,
    CustomUserManager,
    EmailOTP,
    StudentProfile,
    FacultyProfile,
    LoginAttempt,
)

__all__ = [
    "UUIDModel",
    "TimeStampedModel",
    "CreatedByModel",
    "User",
    "CustomUserManager",
    "EmailOTP",
    "StudentProfile",
    "FacultyProfile",
    "LoginAttempt",
]
