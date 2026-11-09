"""
AssessmentResult model for Assessment Management.

Final result of an assessment for a student.
"""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.conf import settings

from users.models.base import CreatedByModel, TimeStampedModel, UUIDModel


class AssessmentResult(UUIDModel, TimeStampedModel):
    """
    Final result of an assessment for a student.

    Links to assessment and student with final marks.
    """

    assessment = models.ForeignKey(
        "Assessment",
        on_delete=models.CASCADE,
        related_name="results",
        help_text="Assessment",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assessment_results",
        limit_choices_to={"role": "student"},
        help_text="Student",
    )

    total_marks_obtained = models.PositiveIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(1000)]
    )
    percentage = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    passed = models.BooleanField(help_text="Whether student passed")

    attempted_at = models.DateTimeField()
    evaluated_at = models.DateTimeField(auto_now_add=True)

    # Optional feedback
    feedback = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "assessments_assessmentresult"
        unique_together = [["assessment", "student"]]
        ordering = ["-evaluated_at"]
        indexes = [
            models.Index(fields=["student"], name="asres_student_idx"),
        ]

    def __str__(self):
        return f"{self.assessment.title} - {self.student.email}: {self.total_marks_obtained}/{self.assessment.total_marks}"
