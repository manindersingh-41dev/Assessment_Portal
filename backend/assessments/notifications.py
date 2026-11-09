"""Scheduling helpers for grouped assessment assignment emails."""

import uuid
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import AssessmentNotification

REMINDER_LEAD_TIME = timedelta(hours=24)


def reminder_send_time(deadline, now=None):
    """Schedule a reminder 24 hours early, or halfway through shorter windows."""
    now = now or timezone.now()
    remaining = deadline - now
    if remaining <= timedelta(0):
        return None
    if remaining <= REMINDER_LEAD_TIME:
        return now + remaining / 2
    return deadline - REMINDER_LEAD_TIME


def enqueue_notification_group(notifications, batch_id=None):
    """Queue due notification records as one email to their assigned students."""
    from .tasks import send_assessment_notification_batch

    notifications = list(notifications)
    if not notifications:
        return
    kind = notifications[0].kind
    if any(notification.kind != kind for notification in notifications):
        raise ValueError("A grouped email can contain only one notification type.")

    now = timezone.now()
    due_ids = [
        notification.id
        for notification in notifications
        if not notification.scheduled_for or notification.scheduled_for <= now
    ]
    if not due_ids:
        return
    batch_id = batch_id or uuid.uuid4()

    try:
        with transaction.atomic():
            queued = list(
                AssessmentNotification.objects.select_for_update().filter(
                    id__in=due_ids,
                    status=AssessmentNotification.Status.PENDING,
                )
            )
            if not queued:
                return
            AssessmentNotification.objects.filter(
                id__in=[notification.id for notification in queued],
            ).update(
                status=AssessmentNotification.Status.QUEUED,
                email_batch_id=batch_id,
                updated_at=now,
            )
        send_assessment_notification_batch.delay(str(batch_id), kind)
    except Exception as exc:
        AssessmentNotification.objects.filter(
            email_batch_id=batch_id,
            kind=kind,
            status=AssessmentNotification.Status.QUEUED,
        ).update(
            status=AssessmentNotification.Status.FAILED,
            last_error=f"Could not queue email: {exc}"[:1000],
            updated_at=timezone.now(),
        )


def schedule_assignment_notifications(assignments):
    """Create one assignment email batch and per-student reminder records."""
    assignments = list(assignments)
    if not assignments:
        return

    now = timezone.now()
    assignment_batch_id = uuid.uuid4()
    reminder_batch_id = uuid.uuid4()
    assignment_notices = []
    reminders = []

    for assignment in assignments:
        assigned_notice, _ = AssessmentNotification.objects.get_or_create(
            assignment=assignment,
            kind=AssessmentNotification.Kind.ASSIGNED,
            defaults={
                "status": AssessmentNotification.Status.PENDING,
                "scheduled_for": now,
                "email_batch_id": assignment_batch_id,
            },
        )
        assignment_notices.append(assigned_notice)

        deadline = assignment.effective_deadline()
        reminder_at = reminder_send_time(deadline, now) if deadline else None
        reminder, _ = AssessmentNotification.objects.get_or_create(
            assignment=assignment,
            kind=AssessmentNotification.Kind.REMINDER,
            defaults={
                "status": (
                    AssessmentNotification.Status.PENDING
                    if reminder_at
                    else AssessmentNotification.Status.SKIPPED
                ),
                "scheduled_for": reminder_at,
                "email_batch_id": reminder_batch_id,
                "last_error": "No upcoming deadline to remind about." if not reminder_at else "",
            },
        )
        if reminder.status == AssessmentNotification.Status.PENDING:
            reminders.append(reminder)

    enqueue_notification_group(assignment_notices, assignment_batch_id)
    enqueue_notification_group(reminders, reminder_batch_id)


def reschedule_reminder_for_started_assignment(assignment):
    """Move a pending reminder to the student's actual completion deadline."""
    notification = AssessmentNotification.objects.filter(
        assignment=assignment,
        kind=AssessmentNotification.Kind.REMINDER,
        status__in=[
            AssessmentNotification.Status.PENDING,
            AssessmentNotification.Status.QUEUED,
        ],
    ).first()
    if not notification:
        return

    now = timezone.now()
    deadline = assignment.effective_deadline()
    reminder_at = reminder_send_time(deadline, now) if deadline else None
    if not reminder_at:
        notification.status = AssessmentNotification.Status.SKIPPED
        notification.scheduled_for = None
        notification.last_error = "The student has no remaining assessment deadline."
        notification.save(update_fields=[
            "status", "scheduled_for", "last_error", "updated_at",
        ])
        return

    notification.scheduled_for = reminder_at
    notification.status = AssessmentNotification.Status.PENDING
    notification.email_batch_id = uuid.uuid4()
    notification.save(update_fields=[
        "status", "scheduled_for", "email_batch_id", "updated_at",
    ])
    enqueue_notification_group([notification])


def reschedule_reminders_for_assessment(assessment):
    """Recalculate pending reminders after faculty changes the schedule."""
    assignments = assessment.assignments.filter(
        notifications__kind=AssessmentNotification.Kind.REMINDER,
        notifications__status__in=[
            AssessmentNotification.Status.PENDING,
            AssessmentNotification.Status.QUEUED,
        ],
    ).distinct().prefetch_related("notifications")
    for assignment in assignments:
        reschedule_reminder_for_started_assignment(assignment)
