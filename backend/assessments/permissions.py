"""
Permission classes for Assessment Management.

Controls access to assessment endpoints based on user role and ownership.
"""

from rest_framework import permissions


class IsApprovedFaculty(permissions.BasePermission):
    """Only approved faculty can access."""

    def has_permission(self, request, view):
        """Check if user is approved faculty."""
        user = request.user
        return (
            user
            and user.is_authenticated
            and user.role == 'faculty'
            and user.is_faculty_approved
        )


class IsAssessmentCreator(permissions.BasePermission):
    """Only assessment creator can modify."""

    def has_object_permission(self, request, view, obj):
        """Check if user is the assessment creator."""
        return obj.created_by == request.user


class CanAssignAssessment(permissions.BasePermission):
    """Only assessment creator can assign."""

    def has_object_permission(self, request, view, obj):
        """Check if user is the assessment creator."""
        return obj.assessment.created_by == request.user


class IsStudent(permissions.BasePermission):
    """Only students can access."""

    def has_permission(self, request, view):
        """Check if user is a student."""
        user = request.user
        return user and user.is_authenticated and user.role == 'student'


class CanViewAssignment(permissions.BasePermission):
    """Student can view own assignment, faculty can view their assessment assignments."""

    def has_object_permission(self, request, view, obj):
        """Check permission to view assignment."""
        user = request.user

        if user.role == 'student':
            return obj.student == user

        if user.role == 'faculty':
            return obj.assessment.created_by == user

        return False
