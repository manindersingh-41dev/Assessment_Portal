"""
URL routing for Results and Submission Management.

Configures API endpoints for results viewing and export.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .result_views import StudentSubmissionViewSet, FacultyResultViewSet

router = DefaultRouter()
router.register(r'submissions', StudentSubmissionViewSet, basename='student-submission')
router.register(r'faculty', FacultyResultViewSet, basename='faculty-result')

urlpatterns = [
    path('', include(router.urls)),
]
