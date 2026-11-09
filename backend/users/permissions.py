"""
Permission classes for role-based access control.

Implements permissions for protecting APIs based on user roles and status.
"""

from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied

from .models import User


class IsStudent(permissions.BasePermission):
    """Permission that allows only students."""

    message = 'Only students can access this endpoint.'

    def has_permission(self, request, view):
        """Check if user is a student."""
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_student()
            and request.user.can_use_system()
        )


class IsFaculty(permissions.BasePermission):
    """Permission that allows only faculty."""

    message = 'Only faculty can access this endpoint.'

    def has_permission(self, request, view):
        """Check if user is faculty."""
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_faculty()
            and request.user.can_manage_assessments()
        )


class IsApprovedFaculty(permissions.BasePermission):
    """Permission that allows only approved faculty."""

    message = 'Faculty account must be approved by administrator.'

    def has_permission(self, request, view):
        """Check if user is approved faculty."""
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_faculty()
            and request.user.is_faculty_approved
            and request.user.can_use_system()
        )


class IsAdmin(permissions.BasePermission):
    """Permission that allows only admin users."""

    message = 'Only administrators can access this endpoint.'

    def has_permission(self, request, view):
        """Check if user is admin."""
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_staff
            and request.user.is_superuser
        )


class IsEmailVerified(permissions.BasePermission):
    """Permission that requires email verification."""

    message = 'Email verification is required.'

    def has_permission(self, request, view):
        """Check if user's email is verified."""
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_email_verified
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    """Permission that allows owner or admin to access."""

    message = 'You do not have permission to access this resource.'

    def has_object_permission(self, request, view, obj):
        """Check if user is owner or admin."""
        return obj == request.user or request.user.is_staff


class CanSubmitCode(permissions.BasePermission):
    """Permission that allows only students to submit code."""

    message = 'Only verified students can submit code.'

    def has_permission(self, request, view):
        """Check if user can submit code."""
        return (
            request.user
            and request.user.is_authenticated
            and request.user.can_submit_code()
        )


class CanManageAssessments(permissions.BasePermission):
    """Permission that allows only faculty to manage assessments."""

    message = 'Only approved faculty can manage assessments.'

    def has_permission(self, request, view):
        """Check if user can manage assessments."""
        return (
            request.user
            and request.user.is_authenticated
            and request.user.can_manage_assessments()
        )


class IsActiveUser(permissions.BasePermission):
    """Permission that requires active user account."""

    message = 'User account is inactive.'

    def has_permission(self, request, view):
        """Check if user account is active."""
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_active
        )
