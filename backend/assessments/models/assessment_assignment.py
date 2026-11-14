"""
AssessmentAssignment model.

Assigns an assessment to a specific student. Tracks whether the student has
started and whether they can still attempt. One assignment per
(assessment, student) pair.
"""

from datetime import timedelta

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from users.models.base import CreatedByModel, TimeStampedModel, UUIDModel


class AssessmentAssignment(UUIDModel, TimeStampedModel, CreatedByModel):
    """
    Assignment of an assessment to a student.

    Created by faculty. A student views/attempts only assessments assigned to
    them. ``started_at``/``submitted_at`` track attempt progress.
    """

    class Status(models.TextChoices):
        ASSIGNED = "assigned", _("Assigned")
        STARTED = "started", _("Started")
        SUBMITTED = "submitted", _("Submitted")
        GRADED = "graded", _("Graded")
        EXPIRED = "expired", _("Expired")

    assessment = models.ForeignKey(
        "assessments.Assessment",
        on_delete=models.CASCADE,
        related_name="assignments",
        help_text="The assessment being assigned.",
    )
    student = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="assessment_assignments",
        limit_choices_to={"role": "student"},
        help_text="The student this assessment is assigned to.",
    )
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=Status.choices,
        default=Status.ASSIGNED,
        db_index=True,
    )
    started_at = models.DateTimeField(
        _("started at"),
        null=True,
        blank=True,
        help_text="When the student started attempting the assessment.",
    )
    submitted_at = models.DateTimeField(
        _("submitted at"),
        null=True,
        blank=True,
        help_text="When the student submitted the assessment.",
    )
    due_at = models.DateTimeField(
        _("due at"),
        null=True,
        blank=True,
        help_text="Optional deadline for this specific assignment.",
    )
    is_flagged_cheating = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether an integrity rule flagged this assessment attempt.",
    )
    cheating_flag_reason = models.CharField(max_length=64, blank=True)
    cheating_flag_speed_wpm = models.FloatField(null=True, blank=True)
    cheating_flag_sustained_ms = models.PositiveIntegerField(null=True, blank=True)
    cheating_flagged_at = models.DateTimeField(null=True, blank=True)
    cheating_flag_cleared_at = models.DateTimeField(null=True, blank=True)
    cheating_flag_cleared_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assessment_cheating_flags_cleared",
    )

    class Meta:
        verbose_name = _("assessment assignment")
        verbose_name_plural = _("assessment assignments")
        ordering = ["-created_at"]
        unique_together = [("assessment", "student")]
        indexes = [
            models.Index(
                fields=["student", "status"], name="assignment_student_status_idx"
            ),
            models.Index(
                fields=["assessment", "student"], name="assessment_assignment_idx"
            ),
            models.Index(fields=["status"], name="assignment_status_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["assessment", "student"],
                name="unique_assessment_student_assignment",
            ),
        ]

    def __str__(self):
        return f"{self.student.email} <- {self.assessment.title}"

    def effective_deadline(self):
        """Return the earliest scheduled, personal, or timed-attempt deadline."""
        deadlines = [self.assessment.end_time]
        if self.due_at:
            deadlines.append(self.due_at)
        if self.started_at and self.assessment.is_timed:
            deadlines.append(
                self.started_at + timedelta(minutes=self.assessment.duration_minutes)
            )
        return min(deadlines) if deadlines else None

    def can_start(self):
        """Check that this assigned assessment can be started or resumed."""
        now = timezone.now()
        if not self.assessment.is_published:
            return False
        if self.status == self.Status.STARTED:
            deadline = self.effective_deadline()
            return bool(self.started_at and (deadline is None or now <= deadline))
        deadline = self.effective_deadline()
        return (
            self.status == self.Status.ASSIGNED
            and self.assessment.start_time <= now
            and (deadline is None or now <= deadline)
        )

    def mark_started(self):
        """Start the assessment attempt and record its start time."""
        if self.status == self.Status.ASSIGNED:
            if not self.can_start():
                raise ValueError("This assessment cannot be started right now.")
            self.status = self.Status.STARTED
            self.started_at = timezone.now()
            self.save(update_fields=["status", "started_at", "updated_at"])
        return self

    def mark_submitted(self):
        """Mark the assessment attempt as submitted."""
        if self.status != self.Status.STARTED:
            raise ValueError("Only a started assessment can be submitted.")
        self.status = self.Status.SUBMITTED
        self.submitted_at = timezone.now()
        self.save(update_fields=["status", "submitted_at", "updated_at"])
        return self
