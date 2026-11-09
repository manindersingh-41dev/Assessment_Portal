"""
TestCaseResult model.

Records the outcome of running a student's submission against a specific
test case.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from users.models.base import TimeStampedModel, UUIDModel


class TestCaseResult(UUIDModel, TimeStampedModel):
    """
    Evaluation result for a specific test case within a submission.

    ``submission`` is the parent student submission. ``test_case`` is the
    question's test case that was run. ``status`` captures the execution
    outcome (passed/failed/error). ``execution_time`` and ``memory_usage``
    can track resource consumption.
    """

    class Status(models.TextChoices):
        PASSED = "passed", _("Passed")
        FAILED = "failed", _("Failed")
        ERROR = "error", _("Error")
        TIMEOUT = "timeout", _("Timeout")
        MEMORY_LIMIT_EXCEEDED = "memory_limit_exceeded", _("Memory Limit Exceeded")

    submission = models.ForeignKey(
        "submissions.Submission",
        on_delete=models.CASCADE,
        related_name="test_case_results",
        help_text="The submission this result belongs to.",
    )
    test_case = models.ForeignKey(
        "questions.TestCase",
        on_delete=models.CASCADE,
        related_name="results",
        help_text="The test case that was evaluated.",
    )
    status = models.CharField(
        _("status"),
        max_length=30,
        choices=Status.choices,
        db_index=True,
    )
    actual_output = models.TextField(
        _("actual output"),
        blank=True,
        help_text="The output produced by the student's program.",
    )
    error_message = models.TextField(
        _("error message"),
        blank=True,
        help_text="Execution error / runtime error details, if any.",
    )
    execution_time = models.FloatField(
        _("execution time"),
        null=True,
        blank=True,
        help_text="Time taken in seconds.",
    )
    memory_usage = models.IntegerField(
        _("memory usage"),
        null=True,
        blank=True,
        help_text="Memory used in KB.",
    )
    is_passed = models.BooleanField(
        _("is passed"),
        default=False,
        help_text="Derived from status, true if status is PASSED.",
    )

    class Meta:
        verbose_name = _("test case result")
        verbose_name_plural = _("test case results")
        ordering = ["test_case__order"]
        indexes = [
            models.Index(fields=["submission", "status"], name="tc_result_sub_status_idx"),
            models.Index(fields=["status"], name="tc_result_status_idx"),
        ]

    def __str__(self):
        return f"Result {self.id} for Submission {self.submission_id} (TC: {self.test_case_id})"

    def save(self, *args, **kwargs):
        # Automatically set is_passed based on status
        self.is_passed = self.status == self.Status.PASSED
        super().save(*args, **kwargs)
