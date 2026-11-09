"""
URL routing for Code Submissions.

Configures API endpoints for submissions.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CodeSubmissionViewSet, SubmissionCreateView,
    SubmissionStatusView, SubmissionListView, RunCodeView,
    ExecutionCasesView, ClientEvaluationCreateView,
    ClientEvaluationResultsView,
)

router = DefaultRouter()
router.register(r'submissions', CodeSubmissionViewSet, basename='submission')
router.register(r'create', SubmissionCreateView, basename='create-submission')
router.register(r'status', SubmissionStatusView, basename='submission-status')
router.register(r'list', SubmissionListView, basename='submission-list')

urlpatterns = [
    path('run/', RunCodeView.as_view(), name='submission-run'),
    path(
        'execution-cases/',
        ExecutionCasesView.as_view(),
        name='client-execution-cases',
    ),
    path(
        'client-evaluations/',
        ClientEvaluationCreateView.as_view(),
        name='client-evaluation-create',
    ),
    path(
        'client-evaluations/<uuid:submission_id>/results/',
        ClientEvaluationResultsView.as_view(),
        name='client-evaluation-results',
    ),
    path('', include(router.urls)),
]
