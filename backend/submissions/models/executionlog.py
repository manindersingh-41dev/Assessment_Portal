"""
ExecutionLog model for submissions management.

Detailed logs of execution process for debugging.
Stores compilation and execution logs.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from users.models.base import TimeStampedModel, UUIDModel


class ExecutionLog(UUIDModel, TimeStampedModel):
    """
    Detailed logs of execution process for debugging.

    Stores compilation and execution logs.
    """

    class LogLevel(models.TextChoices):
        DEBUG = "debug", _("Debug")
        INFO = "info", _("Info")
        WARNING = "warning", _("Warning")
        ERROR = "error", _("Error")

    submission = models.OneToOneField(
        "submissions.CodeSubmission",
        on_delete=models.CASCADE,
        related_name="execution_log",
        help_text="Submission this log belongs to",
    )

    # Phases
    compilation_output = models.TextField(
        blank=True,
        null=True,
        help_text="Compiler stdout",
    )
    compilation_stderr = models.TextField(
        blank=True,
        null=True,
        help_text="Compiler stderr",
    )

    # Execution
    execution_output = models.TextField(
        blank=True,
        null=True,
        help_text="Execution output/logs",
    )

    # System
    system_info = models.JSONField(
        default=dict,
        help_text="System information (container, etc.)",
    )

    class Meta:
        db_table = "submissions_executionlog"

    def __str__(self):
        return f"Log for {self.submission.id}"
