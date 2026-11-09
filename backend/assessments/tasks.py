"""Background delivery for grouped assessment assignment emails."""

import logging
import random
from collections import defaultdict
from datetime import timedelta
import uuid

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage
from django.db import transaction
from django.utils import timezone

from .models import AssessmentAssignment, AssessmentNotification
from .notifications import enqueue_notification_group

logger = logging.getLogger(__name__)
EMAIL_RETRY_DELAY = timedelta(minutes=5)
STALE_SEND_AFTER = timedelta(minutes=10)
MAX_EMAIL_ATTEMPTS = 4


def _email_content(notifications):
    notification = notifications[0]
    assessment = notification.assignment.assessment
    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173").rstrip("/")
    assessment_url = f"{frontend_url}/student/assessments/{assessment.id}"
    start_text = timezone.localtime(assessment.start_time).strftime(
        "%A, %B %d, %Y at %I:%M %p %Z"
    )
    end_text = timezone.localtime(assessment.end_time).strftime(
        "%A, %B %d, %Y at %I:%M %p %Z"
    )
    if notification.kind == AssessmentNotification.Kind.ASSIGNED:
        subject = f"Assessment assigned: {assessment.title}"
        intro = f"{assessment.title} has been assigned to you."
    else:
        subject = f"Assessment deadline reminder: {assessment.title}"
        intro = f"This is a reminder about the upcoming deadline for {assessment.title}."

    time_limit = (
        f"{assessment.duration_minutes} minutes after starting"
        if assessment.is_timed
        else "No completion time limit after starting"
    )
    message = (
        f"Hello,\n\n{intro}\n\n"
        f"Available from: {start_text}\n"
        f"Scheduled window closes: {end_text}\n"
        f"Time limit: {time_limit}\n"
        "If a personal deadline applies to you, sign in to see its date and time.\n\n"
        f"Open the assessment: {assessment_url}\n\n"
        "If you have already submitted the assessment, you can ignore this message."
    )
    return subject, message


@shared_task
def send_assessment_notification_batch(batch_id, kind):
    """Send one email with one student in To and other recipients in CC."""
    now = timezone.now()
    try:
        with transaction.atomic():
            notifications = list(
                AssessmentNotification.objects.select_for_update().select_related(
                    "assignment__assessment", "assignment__student",
                ).filter(
                    email_batch_id=batch_id,
                    kind=kind,
                    status=AssessmentNotification.Status.QUEUED,
                )
            )
            if not notifications:
                return {"status": "already_processed"}

            eligible = []
            for notification in notifications:
                assignment = notification.assignment
                if notification.scheduled_for and now < notification.scheduled_for:
                    notification.status = AssessmentNotification.Status.PENDING
                    notification.save(update_fields=["status", "updated_at"])
                    continue

                if notification.kind == AssessmentNotification.Kind.REMINDER:
                    deadline = assignment.effective_deadline()
                    if (
                        assignment.status in {
                            AssessmentAssignment.Status.SUBMITTED,
                            AssessmentAssignment.Status.GRADED,
                            AssessmentAssignment.Status.EXPIRED,
                        }
                        or deadline is None
                        or deadline <= now
                    ):
                        notification.status = AssessmentNotification.Status.SKIPPED
                        notification.last_error = (
                            "The student has already submitted or has no upcoming deadline."
                        )
                        notification.save(update_fields=[
                            "status", "last_error", "updated_at",
                        ])
                        continue

                notification.status = AssessmentNotification.Status.SENDING
                notification.attempts += 1
                notification.save(update_fields=["status", "attempts", "updated_at"])
                eligible.append(notification)

    except AssessmentNotification.DoesNotExist:
        logger.warning("Assessment notification batch %s no longer exists", batch_id)
        return {"status": "missing"}

    if not eligible:
        return {"status": "skipped_or_rescheduled"}

    recipient_emails = list(dict.fromkeys(
        notification.assignment.student.email
        for notification in eligible
        if notification.assignment.student.email
    ))
    if not recipient_emails:
        _record_email_failure(eligible, "Assigned students do not have email addresses.")
        return {"status": "failed"}

    primary_recipient = random.choice(recipient_emails)
    cc_recipients = [email for email in recipient_emails if email != primary_recipient]
    try:
        subject, message = _email_content(eligible)
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[primary_recipient],
            cc=cc_recipients,
        )
        if email.send(fail_silently=False) != 1:
            raise RuntimeError("Email service did not accept the message.")

        sent_at = timezone.now()
        AssessmentNotification.objects.filter(
            id__in=[notification.id for notification in eligible],
            status=AssessmentNotification.Status.SENDING,
        ).update(
            status=AssessmentNotification.Status.SENT,
            sent_at=sent_at,
            last_error="",
            updated_at=sent_at,
        )
        return {"status": "sent", "recipient_count": len(recipient_emails)}
    except Exception as exc:
        _record_email_failure(eligible, str(exc))
        logger.warning("Assessment email batch %s failed", batch_id, exc_info=True)
        return {"status": "retry_scheduled"}


def _record_email_failure(notifications, error):
    now = timezone.now()
    retry_at = now + EMAIL_RETRY_DELAY
    for notification in notifications:
        notification.last_error = str(error)[:1000]
        if notification.attempts >= MAX_EMAIL_ATTEMPTS:
            notification.status = AssessmentNotification.Status.FAILED
            notification.save(update_fields=["status", "last_error", "updated_at"])
        else:
            notification.status = AssessmentNotification.Status.PENDING
            notification.scheduled_for = retry_at
            notification.save(update_fields=[
                "status", "scheduled_for", "last_error", "updated_at",
            ])


@shared_task
def queue_due_assessment_notifications():
    """Recover due email work and dispatch it from persistent database state."""
    now = timezone.now()
    stale_before = now - STALE_SEND_AFTER
    stale_groups = list(
        AssessmentNotification.objects.filter(
            status__in=[
                AssessmentNotification.Status.SENDING,
                AssessmentNotification.Status.QUEUED,
            ],
            updated_at__lt=stale_before,
        ).values_list("email_batch_id", "kind").distinct()
    )
    for batch_id, kind in stale_groups:
        AssessmentNotification.objects.filter(
            email_batch_id=batch_id,
            kind=kind,
            status__in=[
                AssessmentNotification.Status.SENDING,
                AssessmentNotification.Status.QUEUED,
            ],
        ).update(
            status=AssessmentNotification.Status.PENDING,
            scheduled_for=now,
            last_error="An earlier email job stopped before recording delivery.",
            updated_at=now,
        )

    due_notifications = AssessmentNotification.objects.filter(
        status=AssessmentNotification.Status.PENDING,
        scheduled_for__lte=now,
    ).select_related("assignment__assessment").order_by("scheduled_for")
    due_groups = defaultdict(list)
    for notification in due_notifications[:1000]:
        key = (notification.assignment.assessment_id, notification.kind)
        due_groups[key].append(notification)

    for notifications in due_groups.values():
        enqueue_notification_group(notifications, uuid.uuid4())
    return {"queued_groups": len(due_groups)}
