"""
URL routing for Question Bank API.

Maps endpoints for question and test case management.
"""

from django.urls import path

from .views import (
    question_bulk_create,
    question_detail,
    question_list_create,
    question_test_cases,
    test_case_detail,
    test_case_list_create,
)


urlpatterns = [
    path('questions/bulk/', question_bulk_create, name='question-bulk-create'),
    path('questions/', question_list_create, name='question-list-create'),
    path('questions/<uuid:pk>/test_cases/', question_test_cases, name='question-test-cases'),
    path('questions/<uuid:pk>/', question_detail, name='question-detail'),
    path('test-cases/', test_case_list_create, name='test-case-list-create'),
    path('test-cases/<uuid:pk>/', test_case_detail, name='test-case-detail'),
]
