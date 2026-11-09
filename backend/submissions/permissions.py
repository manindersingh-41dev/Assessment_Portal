"""
Permissions for Code Submissions.

Controls access to submission endpoints.
"""

from rest_framework import permissions


class IsStudent(permissions.BasePermission):
    """Only students can access."""

    def has_permission(self, request, view):
        """Check if user is a student."""
        user = request.user
        return user and user.is_authenticated and user.role == 'student'


class IsOwnSubmission(permissions.BasePermission):
    """Only student who submitted can view their submission."""

    def has_object_permission(self, request, view, obj):
        """Check if user owns the submission."""
        return obj.student == request.user


class CanViewSubmissionResult(permissions.BasePermission):
    """Student can view own submission, faculty can view assignment submissions."""

    def has_object_permission(self, request, view, obj):
        """Check permission to view submission result."""
        user = request.user

        if user.role == 'student':
            return obj.student == user

        if user.role == 'faculty':
            return obj.assignment.assessment.created_by == user

        return False
