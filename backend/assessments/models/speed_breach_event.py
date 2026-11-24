"""Idempotent audit records for assessment integrity events."""

import uuid

from django.conf import settings
from django.db import models


class AssessmentIntegrityEvent(models.Model):
    class EventType(models.TextChoices):
        SPEED = "high_code_writing_speed", "High code-writing speed"
        RAPID_CODE_INSERTION = "rapid_code_insertion", "Rapid code insertion"
        BULK_CODE_INSERTION = "bulk_code_insertion", "Bulk code insertion"
        TAB_HIDDEN = "tab_hidden", "Assessment tab hidden"
        WINDOW_BLUR = "window_blur", "Assessment window lost focus"
        FULLSCREEN_EXIT = "fullscreen_exit", "Fullscreen exited"

    class Outcome(models.TextChoices):
        WARNING = "warning", "Warning"
        LOCKED = "locked", "Coding window locked"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="integrity_events",
    )
    assignment = models.ForeignKey(
        "assessments.AssessmentAssignment",
        on_delete=models.CASCADE,
        related_name="integrity_events",
    )
    event_id = models.UUIDField()
    event_type = models.CharField(max_length=32, choices=EventType.choices)
    speed_wpm = models.FloatField(null=True, blank=True)
    words_per_second = models.FloatField(null=True, blank=True)
    sustained_ms = models.PositiveIntegerField(null=True, blank=True)
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
