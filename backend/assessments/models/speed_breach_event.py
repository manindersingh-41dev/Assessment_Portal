"""Idempotent audit records for sustained code-writing speed breaches."""

import uuid

from django.conf import settings
from django.db import models


class AssessmentSpeedBreachEvent(models.Model):
    class Outcome(models.TextChoices):
        WARNING = "warning", "Warning"
        LOCKED = "locked", "Coding window locked"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="speed_breach_events",
    )
    assignment = models.ForeignKey(
        "assessments.AssessmentAssignment",
        on_delete=models.CASCADE,
        related_name="speed_breach_events",
    )
    event_id = models.UUIDField()
    speed_wpm = models.FloatField()
    sustained_ms = models.PositiveIntegerField()
    outcome = models.CharField(
        max_length=12,
        choices=Outcome.choices,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "event_id"],
                name="uq_student_speed_event",
            ),
        ]
        indexes = [
            models.Index(
                fields=["student", "outcome"],
                name="ix_speed_evt_student_outcome",
            ),
        ]
