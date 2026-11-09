"""
Management command to verify complete backend integration.

Usage: python manage.py check_integration
"""

import logging
from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Django management command for integration verification."""

    help = "Verify complete backend integration and configuration"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show detailed output",
        )
        parser.add_argument(
            "--check-database",
            action="store_true",
            help="Verify database connectivity",
        )

    def handle(self, *args, **options):
        """Execute integration check."""
        self.stdout.write(
            self.style.SUCCESS("\n" + "=" * 70)
        )
        self.stdout.write(
            self.style.SUCCESS("GEETA UNIVERSITY CODING ASSESSMENT PORTAL")
        )
        self.stdout.write(
            self.style.SUCCESS("Backend Integration Verification")
        )
        self.stdout.write(
            self.style.SUCCESS("=" * 70 + "\n")
        )

        verbose = options.get("verbose", False)
        check_db = options.get("check_database", False)

        # Check apps
        self.stdout.write(self.style.HTTP_INFO("\n[1] Checking Django Apps..."))
        self._check_apps(verbose)

        # Check models
        self.stdout.write(self.style.HTTP_INFO("\n[2] Checking Models..."))
        self._check_models(verbose)

        # Check relationships
        self.stdout.write(
            self.style.HTTP_INFO("\n[3] Checking Database Relationships...")
        )
        self._check_relationships(verbose)

        # Check permissions
        self.stdout.write(
            self.style.HTTP_INFO("\n[4] Checking Permission Classes...")
        )
        self._check_permissions(verbose)

        # Check URL configuration
        self.stdout.write(self.style.HTTP_INFO("\n[5] Checking URL Configuration..."))
        self._check_urls(verbose)

        # Check database connectivity
        if check_db:
            self.stdout.write(
                self.style.HTTP_INFO("\n[6] Checking Database Connectivity...")
            )
            self._check_database()

        self.stdout.write(
            self.style.SUCCESS("\n" + "=" * 70)
        )
        self.stdout.write(
            self.style.SUCCESS("✓ Integration verification complete!")
        )
        self.stdout.write(
            self.style.SUCCESS("=" * 70 + "\n")
        )

    def _check_apps(self, verbose):
        """Check all required Django apps are installed."""
        required_apps = [
            "django.contrib.admin",
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "rest_framework",
            "rest_framework_simplejwt",
            "corsheaders",
            "users",
            "questions",
            "assessments",
            "submissions",
            "code_execution",
            "results",
        ]

        installed = [app.name for app in apps.get_app_configs()]
        errors = []

        for app in required_apps:
            if app in installed:
                status = self.style.SUCCESS("✓")
                self.stdout.write(f"  {status} {app}")
            else:
                status = self.style.ERROR("✗")
                self.stdout.write(f"  {status} {app}")
                errors.append(app)

        if errors:
            self.stdout.write(
                self.style.ERROR(f"\n  ERROR: Missing apps: {', '.join(errors)}")
            )

    def _check_models(self, verbose):
        """Check all expected models exist."""
        expected_models = {
            "users": [
                "User",
                "UserVerificationToken",
            ],
            "questions": ["Question", "TestCase"],
            "assessments": [
                "Assessment",
                "AssessmentQuestion",
                "StudentBatch",
                "AssessmentAssignment",
                "AssessmentResult",
            ],
            "submissions": [
                "CodeSubmission",
                "TestCaseVerdict",
                "ExecutionLog",
            ],
        }

        errors = []

        for app_label, model_names in expected_models.items():
            try:
                app_config = apps.get_app_config(app_label)
                app_models = {m.__name__: m for m in app_config.get_models()}

                for model_name in model_names:
                    if model_name in app_models:
                        status = self.style.SUCCESS("✓")
                        self.stdout.write(
                            f"  {status} {app_label}.{model_name}"
                        )
                    else:
                        status = self.style.ERROR("✗")
                        self.stdout.write(
                            f"  {status} {app_label}.{model_name}"
                        )
                        errors.append(f"{app_label}.{model_name}")
            except LookupError as e:
                status = self.style.ERROR("✗")
                self.stdout.write(f"  {status} {app_label}")
                errors.append(str(e))

        if errors:
            self.stdout.write(
                self.style.ERROR(
                    f"\n  ERROR: Missing models: {', '.join(errors)}"
                )
            )

    def _check_relationships(self, verbose):
        """Check database relationships."""
        relationships = [
            ("questions.Question", "created_by"),
            ("assessments.Assessment", "created_by"),
            ("assessments.AssessmentQuestion", "question"),
            ("assessments.AssessmentQuestion", "assessment"),
            ("submissions.CodeSubmission", "assignment"),
            ("submissions.CodeSubmission", "student"),
            ("submissions.TestCaseVerdict", "submission"),
        ]

        errors = []

        for model_path, field_name in relationships:
            try:
                app_label, model_name = model_path.split(".")
                model = apps.get_model(app_label, model_name)
                field = model._meta.get_field(field_name)
                status = self.style.SUCCESS("✓")
                self.stdout.write(
                    f"  {status} {model_path}.{field_name}"
                )
            except Exception as e:
                status = self.style.ERROR("✗")
                self.stdout.write(
                    f"  {status} {model_path}.{field_name}"
                )
                errors.append(f"{model_path}.{field_name}: {str(e)}")

        if errors:
            self.stdout.write(
                self.style.ERROR(
                    f"\n  ERROR: Relationship issues: {errors}"
                )
            )

    def _check_permissions(self, verbose):
        """Check permission classes are available."""
        permission_classes = [
            ("users.permissions", "IsApprovedFaculty"),
            ("users.permissions", "IsStudent"),
            ("questions.permissions", "IsQuestionCreator"),
            ("assessments.permissions", "IsAssessmentCreator"),
            ("submissions.permissions", "IsOwnSubmission"),
        ]

        errors = []

        for module_path, class_name in permission_classes:
            try:
                module = __import__(
                    f"backend.{module_path}", fromlist=[class_name]
                )
                cls = getattr(module, class_name)
                status = self.style.SUCCESS("✓")
                self.stdout.write(
                    f"  {status} {module_path}.{class_name}"
                )
            except Exception as e:
                status = self.style.ERROR("✗")
                self.stdout.write(
                    f"  {status} {module_path}.{class_name}"
                )
                errors.append(f"{module_path}.{class_name}: {str(e)}")

        if errors:
            self.stdout.write(
                self.style.ERROR(
                    f"\n  ERROR: Permission issues: {errors}"
                )
            )

    def _check_urls(self, verbose):
        """Check URL configuration."""
        try:
            from django.urls import get_resolver

            resolver = get_resolver()
            patterns = resolver.url_patterns

            url_checks = [
                "api/users",
                "api/questions",
                "api/assessments",
                "api/submissions",
                "api/results",
            ]

            status = self.style.SUCCESS("✓")
            self.stdout.write(
                f"  {status} URLconf loaded successfully"
            )
            self.stdout.write(
                f"  {status} {len(patterns)} URL patterns registered"
            )

        except Exception as e:
            status = self.style.ERROR("✗")
            self.stdout.write(f"  {status} URLconf error: {str(e)}")

    def _check_database(self):
        """Check database connectivity."""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

            status = self.style.SUCCESS("✓")
            self.stdout.write(f"  {status} Database connection successful")

            # Get database info
            db_vendor = connection.vendor
            db_name = connection.settings_dict.get("NAME", "unknown")
            self.stdout.write(
                f"  {status} Database: {db_vendor} ({db_name})"
            )

        except Exception as e:
            status = self.style.ERROR("✗")
            self.stdout.write(
                f"  {status} Database connection failed: {str(e)}"
            )
