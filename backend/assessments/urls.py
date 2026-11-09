"""
URL routing for Assessment Management.

Configures API endpoints for assessments, assignments, and results.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AssessmentViewSet,
    AssessmentAssignmentViewSet,
)

router = DefaultRouter()
router.register(r'assessments', AssessmentViewSet, basename='assessment')
router.register(r'assignments', AssessmentAssignmentViewSet, basename='assignment')

urlpatterns = [
    path('', include(router.urls)),
]
