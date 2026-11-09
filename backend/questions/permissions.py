"""
Permissions for the questions app.

Faculty can create/manage questions; students can only read active questions
(and only sample test cases are exposed to them via the view layer).
"""

from rest_framework import permissions


class IsFacultyOrReadOnly(permissions.BasePermission):
    """
    Faculty can write; any authenticated user can read active questions.
    """

    message = "Only faculty members can create or modify questions."

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        is_faculty = getattr(request.user, "is_faculty", False)
        if callable(is_faculty):
            is_faculty = is_faculty()
        return bool(
            request.user
            and request.user.is_authenticated
            and is_faculty
        )

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.created_by == request.user


class IsQuestionOwner(permissions.BasePermission):
    """Object-level: only the faculty who created a question may modify it."""

    message = "You do not own this question."

    def has_object_permission(self, request, view, obj):
        return obj.created_by == request.user
