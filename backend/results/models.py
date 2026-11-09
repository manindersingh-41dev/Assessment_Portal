"""
AssessmentResult model.
Summarizes the student's performance on an assessment.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from users.models.base import TimeStampedModel, UUIDModel

class AssessmentResult(UUIDModel, TimeStampedModel):
    """
    Final score for an assessment assignment.
    """
    assignment = models.OneToOneField(
        "assessments.AssessmentAssignment",
        on_delete=models.CASCADE,
        related_name="result",
        help_text="The assignment this result belongs to.",
    )
    total_marks_obtained = models.PositiveSmallIntegerField(
        _("total marks obtained"),
        default=0,
    )
    is_released = models.BooleanField(
        _("is released"),
        default=False,
        help_text="Whether the result has been released to the student.",
    )

    class Meta:
        verbose_name = _("assessment result")
        verbose_name_plural = _("assessment results")
        indexes = [
            models.Index(fields=["is_released"], name="result_released_idx"),
        ]

    def __str__(self):
        return f"Result for Assignment {self.assignment_id}"
