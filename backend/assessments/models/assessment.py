"""
Assessment model.

An assessment is a collection of questions created by faculty, scheduled with a
start and end time, and assigned to students. Total marks is derived from its
questions.
"""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from users.models.base import CreatedByModel, TimeStampedModel, UUIDModel


class Assessment(UUIDModel, TimeStampedModel, CreatedByModel):
    """
    An assessment (exam/quiz) created by faculty.

    Contains a set of questions via ``AssessmentQuestion`` and is assigned to
    students via ``AssessmentAssignment``. Students can attempt it only within
    the [start_time, end_time] window if assigned.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        SCHEDULED = "scheduled", _("Scheduled")
        ACTIVE = "active", _("Active")
        CLOSED = "closed", _("Closed")
        ARCHIVED = "archived", _("Archived")

    title = models.CharField(_("title"), max_length=200, db_index=True)
    description = models.TextField(_("description"), blank=True)
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    start_time = models.DateTimeField(
        _("start time"),
        help_text="Assessment becomes available to students at this time.",
    )
    end_time = models.DateTimeField(
        _("end time"),
        help_text="Assessment is no longer available after this time.",
    )
    duration_minutes = models.PositiveIntegerField(
        _("duration (minutes)"),
        help_text="Duration of the assessment in minutes.",
    )
    is_timed = models.BooleanField(
        _("timed assessment"),
        default=True,
        help_text="Whether students must complete the assessment within duration_minutes.",
    )
    total_marks = models.PositiveSmallIntegerField(
        _("total marks"),
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(1000)],
        help_text="Computed total marks across all questions (managed by service).",
    )
    instructions = models.TextField(_("instructions"), blank=True)
    is_published = models.BooleanField(
        _("published"),
        default=False,
        help_text="Only published assessments are visible to assigned students.",
    )
    published_at = models.DateTimeField(
        _("published at"),
        null=True,
        blank=True,
        db_index=True,
        help_text="When the assessment was first published.",
    )

    class Meta:
        verbose_name = _("assessment")
        verbose_name_plural = _("assessments")
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["status", "start_time", "end_time"],
                name="assessment_status_window_idx",
            ),
            models.Index(
                fields=["created_by", "status"],
                name="assessment_created_by_idx",
            ),
            models.Index(fields=["is_published"], name="assessment_published_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                name="assessment_end_after_start",
                condition=models.Q(end_time__gt=models.F("start_time")),
            ),
            models.CheckConstraint(
                name="assessment_duration_positive",
                condition=models.Q(duration_minutes__gte=1),
            ),
        ]

    def __str__(self):
        return self.title

    @property
    def is_open(self):
        """True if the current time is within the assessment window."""
        from django.utils import timezone

        now = timezone.now()
        return self.start_time <= now <= self.end_time
