"""
CodeSubmission model for submissions management.

A code submission by a student for a question in an assessment.
Stores the source code and tracks execution status and results.
"""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from users.models.base import TimeStampedModel, UUIDModel


class CodeSubmission(UUIDModel, TimeStampedModel):
    """
    A code submission by a student for a question in an assessment.

    Stores the source code and tracks execution status and results.
    """

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        COMPILING = "compiling", _("Compiling")
        COMPILED = "compiled", _("Compiled")
        EXECUTING = "executing", _("Executing")
        COMPLETED = "completed", _("Completed")
        FAILED = "failed", _("Failed")

    class Verdict(models.TextChoices):
        ACCEPTED = "accepted", _("Accepted (All test cases passed)")
        WRONG_ANSWER = "wrong_answer", _("Wrong Answer")
        COMPILATION_ERROR = "compilation_error", _("Compilation Error")
        RUNTIME_ERROR = "runtime_error", _("Runtime Error")
        TIME_LIMIT_EXCEEDED = "time_limit_exceeded", _("Time Limit Exceeded")
        MEMORY_LIMIT_EXCEEDED = "memory_limit_exceeded", _("Memory Limit Exceeded")
        INTERNAL_ERROR = "internal_error", _("Internal Error")
        NOT_EVALUATED = "not_evaluated", _("Not Evaluated")

    class RunnerType(models.TextChoices):
        SERVER_DOCKER = "server_docker", _("Server Docker")
        WEB_WASM = "web_wasm", _("WebAssembly client")
        DESKTOP_GCC = "desktop_gcc", _("Desktop GCC client")

    # Relationships
    assignment = models.ForeignKey(
        "assessments.AssessmentAssignment",
        on_delete=models.CASCADE,
        related_name="submissions",
        help_text="Assignment this submission is for",
    )
    question = models.ForeignKey(
        "assessments.AssessmentQuestion",
        on_delete=models.CASCADE,
        related_name="submissions",
        help_text="Question being solved",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="code_submissions",
        limit_choices_to={"role": "student"},
        help_text="Student who submitted",
    )

    # Code
    source_code = models.TextField(
        help_text="C source code submitted"
    )
    language = models.CharField(
        max_length=20,
        default="c",
        help_text="Programming language (c only in Phase 1)",
    )

    # Execution Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        help_text="Current execution status",
    )

    # Results
    verdict = models.CharField(
        max_length=30,
        choices=Verdict.choices,
        default=Verdict.NOT_EVALUATED,
        db_index=True,
        help_text="Final verdict",
    )
    marks_obtained = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Marks obtained for this submission",
    )

    # Errors
    compilation_error = models.TextField(
        blank=True,
        null=True,
        help_text="Compilation error message (if any)",
    )
    compilation_time_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Time taken to compile (milliseconds)",
    )

    # Execution
    total_test_cases = models.PositiveIntegerField(
        default=0,
        help_text="Total test cases",
    )
    passed_test_cases = models.PositiveIntegerField(
        default=0,
        help_text="Number of passed test cases",
    )
    failed_test_cases = models.PositiveIntegerField(
        default=0,
        help_text="Number of failed test cases",
    )

    # Execution details
    execution_time_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Total execution time across all test cases (ms)",
    )
    max_memory_used_mb = models.FloatField(
        null=True,
        blank=True,
        help_text="Maximum memory used (MB)",
    )

    # Processing
    execution_job_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
        db_index=True,
        help_text="Celery job ID for tracking",
    )
    evaluation_generation = models.PositiveIntegerField(
        default=1,
        help_text="Generation token used to ignore stale or superseded evaluation tasks.",
    )
    execution_started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When execution started",
    )
    execution_completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When execution completed",
    )

    # Metadata
    attempt_number = models.PositiveIntegerField(
        default=1,
        help_text="Attempt number for this question",
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of submitting student",
    )
    runner_type = models.CharField(
        max_length=20,
        choices=RunnerType.choices,
        default=RunnerType.SERVER_DOCKER,
        help_text="Execution environment that produced this submission",
    )
    runner_version = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Version of the client-side runner, when applicable",
    )
    compiler_version = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Compiler version reported by a client-side runner",
    )
    client_submission_id = models.UUIDField(
        null=True,
        blank=True,
        unique=True,
        help_text="Client-generated idempotency key for starting a client evaluation",
    )
    client_request_sha256 = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Hash of the client evaluation creation request for idempotency",
    )
    client_results_sha256 = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Hash of the client result report for idempotency",
    )
    client_test_cases_snapshot = models.JSONField(
        null=True,
        blank=True,
        help_text="Server-side case snapshot used to judge this client evaluation",
    )

    class Meta:
        db_table = "submissions_codesubmission"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["student", "assignment"], name="sub_student_ass_idx"),
            models.Index(fields=["assignment"], name="sub_assignment_idx"),
            models.Index(fields=["status"], name="sub_status_idx"),
            models.Index(fields=["verdict"], name="sub_verdict_idx"),
            models.Index(fields=["execution_job_id"], name="sub_job_id_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                name="passed_less_equal_total",
                condition=models.Q(passed_test_cases__lte=models.F("total_test_cases"))
            ),
            models.CheckConstraint(
                name="failed_plus_passed_equal_total",
                condition=models.Q(
                    models.Q(total_test_cases=0) |
                    models.Q(passed_test_cases__gt=0) |
                    models.Q(failed_test_cases__gt=0)
                )
            ),
        ]

    def __str__(self):
        return f"{self.student.email} - {self.question.question.title} ({self.verdict})"

    @property
    def is_accepted(self):
        """Check if submission is accepted."""
        return self.verdict == self.Verdict.ACCEPTED

    @property
    def is_compilation_error(self):
        """Check if compilation failed."""
        return self.verdict == self.Verdict.COMPILATION_ERROR

    @property
    def is_runtime_error(self):
        """Check if runtime error occurred."""
        return self.verdict == self.Verdict.RUNTIME_ERROR

    def get_success_rate(self):
        """Get success rate as percentage."""
        if self.total_test_cases == 0:
            return 0
        return (self.passed_test_cases / self.total_test_cases) * 100
