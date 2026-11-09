"""Synchronous delivery for grouped assessment assignment emails."""

import logging
import random
import uuid

from django.conf import settings
from django.core.mail import EmailMessage
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import AssessmentNotification

logger = logging.getLogger(__name__)


def _assignment_email_content(notification):
    assessment = notification.assignment.assessment
    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173").rstrip("/")
    assessment_url = f"{frontend_url}/student/assessments/{assessment.id}"
    start_text = timezone.localtime(assessment.start_time).strftime(
        "%A, %B %d, %Y at %I:%M %p %Z"
    )
    end_text = timezone.localtime(assessment.end_time).strftime(
        "%A, %B %d, %Y at %I:%M %p %Z"
    )
    time_limit = (
        f"{assessment.duration_minutes} minutes after starting"
        if assessment.is_timed
        else "No completion time limit after starting"
    )
    message = (
        f"Hello,\n\n{assessment.title} has been assigned to you.\n\n"
        f"Available from: {start_text}\n"
        f"Scheduled window closes: {end_text}\n"
        f"Time limit: {time_limit}\n"
        "If a personal deadline applies to you, sign in to see its date and time.\n\n"
        f"Open the assessment: {assessment_url}\n\n"
        "If you have already submitted the assessment, you can ignore this message."
    )
    return f"Assessment assigned: {assessment.title}", message


def send_notification_group(notifications, batch_id=None):
    """Send one grouped assignment email synchronously through Django's email backend."""
    notifications = list(notifications)
    if not notifications:
        return {"status": "empty"}

    kind = notifications[0].kind
    if any(notification.kind != kind for notification in notifications):
        raise ValueError("A grouped email can contain only one notification type.")
    if kind != AssessmentNotification.Kind.ASSIGNED:
        return {"status": "skipped", "error": "Scheduled reminders are disabled."}

    batch_id = batch_id or notifications[0].email_batch_id or uuid.uuid4()
    notification_ids = [notification.id for notification in notifications]
    now = timezone.now()

    with transaction.atomic():
        eligible = list(
            AssessmentNotification.objects.select_for_update()
            .select_related("assignment__assessment", "assignment__student")
            .filter(
                id__in=notification_ids,
                kind=AssessmentNotification.Kind.ASSIGNED,
                status=AssessmentNotification.Status.PENDING,
            )
        )
        if not eligible:
            return {"status": "already_processed"}

        eligible_ids = [notification.id for notification in eligible]
        AssessmentNotification.objects.filter(id__in=eligible_ids).update(
            status=AssessmentNotification.Status.SENDING,
            email_batch_id=batch_id,
            attempts=F("attempts") + 1,
            updated_at=now,
        )

    recipient_emails = list(dict.fromkeys(
        notification.assignment.student.email
        for notification in eligible
        if notification.assignment.student.email
    ))
    if not recipient_emails:
        error = "Assigned students do not have email addresses."
        AssessmentNotification.objects.filter(id__in=eligible_ids).update(
            status=AssessmentNotification.Status.FAILED,
            last_error=error,
            updated_at=timezone.now(),
        )
        return {"status": "failed", "error": error}

    primary_recipient = random.choice(recipient_emails)
    cc_recipients = [email for email in recipient_emails if email != primary_recipient]
    try:
        subject, message = _assignment_email_content(eligible[0])
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[primary_recipient],
            cc=cc_recipients,
        )
        if email.send(fail_silently=False) != 1:
            raise RuntimeError("Email service did not accept the message.")
    except Exception as exc:
        error = str(exc)[:1000]
        AssessmentNotification.objects.filter(id__in=eligible_ids).update(
            status=AssessmentNotification.Status.FAILED,
            last_error=error,
            updated_at=timezone.now(),
        )
        logger.exception("Assessment assignment email batch %s failed", batch_id)
        return {"status": "failed", "error": error}

    sent_at = timezone.now()
    AssessmentNotification.objects.filter(id__in=eligible_ids).update(
        status=AssessmentNotification.Status.SENT,
        sent_at=sent_at,
        last_error="",
        updated_at=sent_at,
    )
    return {"status": "sent", "recipient_count": len(recipient_emails)}


def send_assignment_notifications(assignments):
    """Create assignment email records and send one grouped email immediately."""
    assignments = list(assignments)
    if not assignments:
        return {"status": "empty"}

    now = timezone.now()
    batch_id = uuid.uuid4()
    notifications = []
    for assignment in assignments:
        notification, _ = AssessmentNotification.objects.get_or_create(
            assignment=assignment,
            kind=AssessmentNotification.Kind.ASSIGNED,
            defaults={
                "status": AssessmentNotification.Status.PENDING,
                "scheduled_for": now,
                "email_batch_id": batch_id,
            },
        )
        notifications.append(notification)

    return send_notification_group(notifications, batch_id)
