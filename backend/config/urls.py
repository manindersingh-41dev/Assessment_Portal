"""
URL configuration for config project (Geeta University Coding Assessment Portal).

The `urlpatterns` list routes URLs to views. API routes are versioned under
``/api/`` and delegated to each app's URL module:

    /api/auth/          -> users app (registration, login, profiles)
    /api/questions/     -> questions app (question bank, test cases)
    /api/assessments/   -> assessments app (assessments, assignments)
    /api/submissions/   -> submissions app (submissions, test case results)
    /api/code/          -> code_execution app (compile/run C programs)
    /api/results/       -> results app (assessment results)
    /admin/             -> Django admin
"""

from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from users.views import StudentDirectoryView

urlpatterns = [
    path("admin/", admin.site.urls),

    # Standard JWT endpoints
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/token/verify/", TokenVerifyView.as_view(), name="token_verify"),

    # App endpoints
    path("api/auth/", include("users.urls")),
    path("api/users/", StudentDirectoryView.as_view(), name="student-directory"),
    path("api/questions/", include("questions.urls")),
    path("api/assessments/", include("assessments.urls")),
    path("api/submissions/", include("submissions.urls")),
    path("api/code/", include("code_execution.urls")),
    path("api/results/", include("results.urls")),
]
