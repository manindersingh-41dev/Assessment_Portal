"""
TestCaseVerdict model for submissions management.

Result of running a test case against a submission.
Stores individual test case results.
"""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from users.models.base import TimeStampedModel, UUIDModel


class TestCaseVerdict(UUIDModel, TimeStampedModel):
    """
    Result of running a test case against a submission.

    Stores individual test case results.
    """

    class Status(models.TextChoices):
        ACCEPTED = "accepted", _("Accepted")
        WRONG_ANSWER = "wrong_answer", _("Wrong Answer")
        RUNTIME_ERROR = "runtime_error", _("Runtime Error")
        TIME_LIMIT_EXCEEDED = "time_limit_exceeded", _("Time Limit Exceeded")
        MEMORY_LIMIT_EXCEEDED = "memory_limit_exceeded", _("Memory Limit Exceeded")

    submission = models.ForeignKey(
        "submissions.CodeSubmission",
        on_delete=models.CASCADE,
        related_name="test_case_verdicts",
        help_text="Submission being tested",
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
        help_text="Test case status",
    )
    marks_obtained = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Marks obtained for this test case",
    )

    # Execution details
    execution_time_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Execution time for this test case (ms)",
    )
    memory_used_mb = models.FloatField(
        null=True,
        blank=True,
        help_text="Memory used for this test case (MB)",
    )

    # Output comparison
    expected_output = models.TextField(
        blank=True,
        null=True,
        help_text="Expected output for visible test cases",
    )
    actual_output = models.TextField(
        blank=True,
        null=True,
        help_text="Actual output from program",
    )
    error_message = models.TextField(
        blank=True,
        null=True,
        help_text="Runtime error message (if any)",
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
