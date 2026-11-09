"""Tracked email notifications for assessment assignments."""

import uuid

from django.db import models

from users.models.base import TimeStampedModel, UUIDModel


class AssessmentNotification(UUIDModel, TimeStampedModel):
    class Kind(models.TextChoices):
        ASSIGNED = "assigned", "Assignment notice"
        REMINDER = "reminder", "Deadline reminder"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        QUEUED = "queued", "Queued"
        SENDING = "sending", "Sending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    assignment = models.ForeignKey(
        "assessments.AssessmentAssignment",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    email_batch_id = models.UUIDField(
        default=uuid.uuid4,
        db_index=True,
        help_text="Identifies the recipients of one grouped assessment email.",
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    scheduled_for = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.TextField(blank=True)

    class Meta:
        ordering = ["kind"]
        indexes = [
            models.Index(fields=["status", "scheduled_for"], name="assess_notif_due_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["assignment", "kind"],
                name="unique_assessment_assignment_notification_kind",
            ),
        ]

    def __str__(self):
        return f"{self.kind} email for {self.assignment_id} ({self.status})"
