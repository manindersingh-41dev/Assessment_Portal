"""Mount the submission and results API under ``/api/results/``."""

from django.urls import include, path

urlpatterns = [path("", include("submissions.result_urls"))]
