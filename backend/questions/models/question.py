"""
Question model for the question bank.

Faculty create questions (C programming problems). Each question carries a
statement, difficulty, language, total marks, and is owned by the faculty
member who created it. Status controls whether the question is active/draft/
archived for use in assessments.
"""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from users.models.base import CreatedByModel, TimeStampedModel, UUIDModel


class Question(UUIDModel, TimeStampedModel, CreatedByModel):
    """
    A programming question in the faculty question bank.

    Used by assessments via the ``AssessmentQuestion`` through model.
    """

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Difficulty(models.TextChoices):
        EASY = "easy", _("Easy")
        MEDIUM = "medium", _("Medium")
        HARD = "hard", _("Hard")

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        ACTIVE = "active", _("Active")
        ARCHIVED = "archived", _("Archived")

    class Language(models.TextChoices):
        C = "c", _("C")

    title = models.CharField(_("title"), max_length=200, db_index=True)
    description = models.TextField(
        _("description"), help_text="Problem statement / description."
    )
    input_format = models.TextField(
        _("input format"), help_text="Explanation of input format."
    )
    output_format = models.TextField(
        _("output format"), help_text="Explanation of output format."
    )
    constraints = models.TextField(
        _("constraints"), help_text="Technical constraints on input data."
    )
    sample_input = models.TextField(
        _("sample input"), help_text="Sample input for display."
    )
    sample_output = models.TextField(
        _("sample output"), help_text="Sample output for display."
    )
    sample_explanation = models.TextField(
        _("sample explanation"),
        blank=True,
        null=True,
        help_text="Explanation for the sample input/output.",
    )
    difficulty = models.CharField(
        _("difficulty"),
        max_length=20,
        choices=Difficulty.choices,
        default=Difficulty.MEDIUM,
        db_index=True,
    )
    topic = models.CharField(
        _("topic"),
        max_length=100,
        blank=True,
        null=True,
        help_text="Topic or tag for the question.",
    )
    language = models.CharField(
        _("language"),
        max_length=20,
        choices=Language.choices,
        default=Language.C,
        help_text="Programming language the question is written for.",
    )
    total_marks = models.PositiveSmallIntegerField(
        _("total marks"),
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text="Maximum marks obtainable for this question.",
    )
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        help_text="Draft questions are not visible to students for assessments.",
    )
    time_limit_seconds = models.PositiveIntegerField(
        _("time limit (seconds)"),
        default=30,
        help_text="Suggested time limit for solving the question.",
    )
    memory_limit_mb = models.PositiveIntegerField(
        _("memory limit (mb)"),
        default=128,
        help_text="Memory limit in MB.",
    )

    class Meta:
        verbose_name = _("question")
        verbose_name_plural = _("questions")
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["status", "difficulty"], name="question_status_difficulty_idx"
            ),
            models.Index(
                fields=["created_by", "status"], name="question_created_by_status_idx"
            ),
            models.Index(fields=["topic"], name="ques_topic_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                name="question_total_marks_positive",
                condition=models.Q(total_marks__gte=1),
            ),
        ]

    def __str__(self):
        return self.title
