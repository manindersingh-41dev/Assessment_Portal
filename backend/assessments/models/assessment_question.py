"""
AssessmentQuestion through model.

Links an Assessment to its Questions with an ordering and per-question marks
within the assessment. This lets faculty reuse the same question across
multiple assessments with different weightings.
"""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from users.models.base import TimeStampedModel, UUIDModel


class AssessmentQuestion(UUIDModel, TimeStampedModel):
    """
    A question included in a specific assessment.

    ``order`` controls the sequence presented to students. ``marks`` is the
    weight of this question within this assessment (may differ from the
    question's default total_marks).
    """

    assessment = models.ForeignKey(
        "assessments.Assessment",
        on_delete=models.CASCADE,
        related_name="assessment_questions",
        help_text="The assessment this question belongs to.",
    )
    question = models.ForeignKey(
        "questions.Question",
        on_delete=models.CASCADE,
        related_name="assessment_questions",
        help_text="The question from the bank included in this assessment.",
    )
    order = models.PositiveSmallIntegerField(
        _("order"),
        default=0,
        help_text="Sequence in which the question is presented to students.",
    )
    marks = models.PositiveSmallIntegerField(
        _("marks"),
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text="Weight of this question within this assessment.",
    )

    class Meta:
        verbose_name = _("assessment question")
        verbose_name_plural = _("assessment questions")
        ordering = ["order", "created_at"]
        unique_together = [("assessment", "question")]
        indexes = [
            models.Index(
                fields=["assessment", "order"],
                name="ass_question_order_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["assessment", "question"],
                name="unique_assessment_question",
            ),
            models.CheckConstraint(
                name="assessment_question_marks_positive",
                condition=models.Q(marks__gte=1),
            ),
        ]

    def __str__(self):
        return f"{self.assessment.title} > {self.question.title}"
