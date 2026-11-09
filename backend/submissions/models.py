"""
Submission Management Models for Geeta University Coding Assessment Portal.

Implements submissions, execution results, and test case verdicts.
"""

import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

from users.models.base import UUIDModel, TimeStampedModel
from assessments.models import AssessmentAssignment, AssessmentQuestion


class CodeSubmission(UUIDModel, TimeStampedModel):
    """
    A code submission by a student for a question in an assessment.

    Stores the source code and tracks execution status and results.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPILING = "compiling", "Compiling"
        COMPILED = "compiled", "Compiled"
        EXECUTING = "executing", "Executing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    class Verdict(models.TextChoices):
        ACCEPTED = "accepted", "Accepted (All test cases passed)"
        WRONG_ANSWER = "wrong_answer", "Wrong Answer"
        COMPILATION_ERROR = "compilation_error", "Compilation Error"
        RUNTIME_ERROR = "runtime_error", "Runtime Error"
        TIME_LIMIT_EXCEEDED = "time_limit_exceeded", "Time Limit Exceeded"
        MEMORY_LIMIT_EXCEEDED = "memory_limit_exceeded", "Memory Limit Exceeded"
        INTERNAL_ERROR = "internal_error", "Internal Error"
        NOT_EVALUATED = "not_evaluated", "Not Evaluated"

    # Relationships
    assignment = models.ForeignKey(
        AssessmentAssignment,
        on_delete=models.CASCADE,
        related_name="submissions",
        help_text="Assignment this submission is for"
    )
    question = models.ForeignKey(
        AssessmentQuestion,
        on_delete=models.CASCADE,
        related_name="submissions",
        help_text="Question being solved"
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="code_submissions",
        limit_choices_to={"role": "student"},
        help_text="Student who submitted"
    )

    # Code
    source_code = models.TextField(
        help_text="C source code submitted"
    )
    language = models.CharField(
        max_length=20,
        default="c",
        help_text="Programming language (c only in Phase 1)"
    )

    # Execution Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        help_text="Current execution status"
    )

    # Results
    verdict = models.CharField(
        max_length=30,
        choices=Verdict.choices,
        default=Verdict.NOT_EVALUATED,
        db_index=True,
        help_text="Final verdict"
    )
    marks_obtained = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Marks obtained for this submission"
    )

    # Errors
    compilation_error = models.TextField(
        blank=True,
        null=True,
        help_text="Compilation error message (if any)"
    )
    compilation_time_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Time taken to compile (milliseconds)"
    )

    # Execution
    total_test_cases = models.PositiveIntegerField(
        default=0,
        help_text="Total test cases"
    )
    passed_test_cases = models.PositiveIntegerField(
        default=0,
        help_text="Number of passed test cases"
    )
    failed_test_cases = models.PositiveIntegerField(
        default=0,
        help_text="Number of failed test cases"
    )

    # Execution details
    execution_time_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Total execution time across all test cases (ms)"
    )
    max_memory_used_mb = models.FloatField(
        null=True,
        blank=True,
        help_text="Maximum memory used (MB)"
    )

    # Processing
    execution_job_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
        db_index=True,
        help_text="Background execution job ID, when available."
    )
    execution_started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When execution started"
    )
    execution_completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When execution completed"
    )

    # Metadata
    attempt_number = models.PositiveIntegerField(
        default=1,
        help_text="Attempt number for this question"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of submitting student"
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


class TestCaseVerdict(UUIDModel, TimeStampedModel):
    """
    Result of running a test case against a submission.

    Stores individual test case results.
    """

    class Status(models.TextChoices):
        ACCEPTED = "accepted", "Accepted"
        WRONG_ANSWER = "wrong_answer", "Wrong Answer"
        RUNTIME_ERROR = "runtime_error", "Runtime Error"
        TIME_LIMIT_EXCEEDED = "time_limit_exceeded", "Time Limit Exceeded"
        MEMORY_LIMIT_EXCEEDED = "memory_limit_exceeded", "Memory Limit Exceeded"

    submission = models.ForeignKey(
        CodeSubmission,
        on_delete=models.CASCADE,
        related_name="test_case_verdicts",
        help_text="Submission being tested"
    )
    test_case_order = models.PositiveIntegerField(
        help_text="Order of test case in question"
    )
    is_sample = models.BooleanField(
        default=False,
        help_text="Whether this is a sample test case"
    )

    # Verdict
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        db_index=True,
        help_text="Test case status"
    )
    marks_obtained = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Marks obtained for this test case"
    )

    # Execution details
    execution_time_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Execution time for this test case (ms)"
    )
    memory_used_mb = models.FloatField(
        null=True,
        blank=True,
        help_text="Memory used for this test case (MB)"
    )

    # Output comparison
    actual_output = models.TextField(
        blank=True,
        null=True,
        help_text="Actual output from program"
    )
    error_message = models.TextField(
        blank=True,
        null=True,
        help_text="Runtime error message (if any)"
    )

    class Meta:
        db_table = "submissions_testcaseverdict"
        unique_together = [["submission", "test_case_order"]]
        ordering = ["test_case_order"]
        indexes = [
            models.Index(fields=["submission", "status"], name="tcv_sub_status_idx"),
        ]

    def __str__(self):
        return f"Test {self.test_case_order} - {self.status}"


class ExecutionLog(UUIDModel, TimeStampedModel):
    """
    Detailed logs of execution process for debugging.

    Stores compilation and execution logs.
    """

    class LogLevel(models.TextChoices):
        DEBUG = "debug", "Debug"
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        ERROR = "error", "Error"

    submission = models.OneToOneField(
        CodeSubmission,
        on_delete=models.CASCADE,
        related_name="execution_log",
        help_text="Submission this log belongs to"
    )

    # Phases
    compilation_output = models.TextField(
        blank=True,
        null=True,
        help_text="Compiler stdout"
    )
    compilation_stderr = models.TextField(
        blank=True,
        null=True,
        help_text="Compiler stderr"
    )

    # Execution
    execution_output = models.TextField(
        blank=True,
        null=True,
        help_text="Execution output/logs"
    )

    # System
    system_info = models.JSONField(
        default=dict,
        help_text="System information (container, etc.)"
    )

    class Meta:
        db_table = "submissions_executionlog"

    def __str__(self):
        return f"Log for {self.submission.id}"
