"""Background delivery for grouped assessment assignment emails."""

from concurrent.futures import ThreadPoolExecutor
import logging
import random
import uuid

from django.conf import settings
from django.core.mail import EmailMessage
from django.db import close_old_connections, transaction
from django.db.models import F
from django.utils import timezone

from .models import AssessmentNotification
from .services import AssignmentService

logger = logging.getLogger(__name__)
ASSESSMENT_EMAIL_CC = "maninder.singh@geetauniversity.edu.in"
_EMAIL_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="assessment-email")


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


def _run_background_job(job, *args):
    """Run a notification job with a thread-local Django database connection."""
    close_old_connections()
    try:
        return job(*args)
    except Exception:
        logger.exception("Background assessment notification job failed")
    finally:
        close_old_connections()


def _submit_background_job(job, *args):
    try:
        _EMAIL_EXECUTOR.submit(_run_background_job, job, *args)
    except RuntimeError:
        logger.exception("Assessment email worker is not accepting jobs")


def _deliver_notification_group(notification_ids, batch_id):
    notifications = list(
        AssessmentNotification.objects.filter(id__in=notification_ids)
    )
    send_notification_group(notifications, batch_id)


def queue_notification_group(notifications, batch_id=None):
    """Mark pending notifications queued and deliver the group off-request."""
    notifications = list(notifications)
    if not notifications:
        return {"status": "empty"}

    batch_id = batch_id or notifications[0].email_batch_id or uuid.uuid4()
    notification_ids = [notification.id for notification in notifications]
    now = timezone.now()

    with transaction.atomic():
        queued_ids = list(
            AssessmentNotification.objects.filter(
                id__in=notification_ids,
                status=AssessmentNotification.Status.PENDING,
            ).values_list("id", flat=True)
        )
        if queued_ids:
            AssessmentNotification.objects.filter(id__in=queued_ids).update(
                status=AssessmentNotification.Status.QUEUED,
                email_batch_id=batch_id,
                scheduled_for=now,
                updated_at=now,
            )
            transaction.on_commit(
                lambda ids=tuple(queued_ids), batch=batch_id: _submit_background_job(
                    _deliver_notification_group, ids, batch
                )
            )

    if not queued_ids:
        return {"status": "already_processed"}
    return {"status": "queued", "recipient_count": len(queued_ids)}


def send_notification_group(notifications, batch_id=None):
    """Send one grouped assignment email through Django's email backend."""
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
                status__in=[
                    AssessmentNotification.Status.PENDING,
                    AssessmentNotification.Status.QUEUED,
                ],
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

    recipients_by_address = {}
    for notification in eligible:
        address = (notification.assignment.student.email or "").strip()
        if address:
            recipients_by_address.setdefault(address.casefold(), address)
    recipient_emails = list(recipients_by_address.values())
    if not recipient_emails:
        error = "Assigned students do not have email addresses."
        AssessmentNotification.objects.filter(id__in=eligible_ids).update(
            status=AssessmentNotification.Status.FAILED,
            last_error=error,
            updated_at=timezone.now(),
        )
        return {"status": "failed", "error": error}

    cc_email = ASSESSMENT_EMAIL_CC
    to_candidates = [
        email for email in recipient_emails
        if email.casefold() != cc_email.casefold()
    ] or recipient_emails
    primary_recipient = random.choice(to_candidates)
    cc_recipients = [cc_email]
    bcc_recipients = [
        email for email in recipient_emails
        if email.casefold() not in {
            primary_recipient.casefold(),
            cc_email.casefold(),
        }
    ]
    try:
        subject, message = _assignment_email_content(eligible[0])
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[primary_recipient],
            cc=cc_recipients,
            bcc=bcc_recipients,
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
    """Create notification records and queue one grouped email in the background."""
    assignments = list(assignments)
    if not assignments:
        return {"status": "empty"}

    now = timezone.now()
    batch_id = uuid.uuid4()
    assignment_ids = list(dict.fromkeys(assignment.id for assignment in assignments))

    with transaction.atomic():
        AssessmentNotification.objects.bulk_create(
            [
                AssessmentNotification(
                    assignment_id=assignment_id,
                    kind=AssessmentNotification.Kind.ASSIGNED,
                    status=AssessmentNotification.Status.PENDING,
                    scheduled_for=now,
                    email_batch_id=batch_id,
                )
                for assignment_id in assignment_ids
            ],
            batch_size=1000,
            ignore_conflicts=True,
        )
        notifications = list(
            AssessmentNotification.objects.filter(
                assignment_id__in=assignment_ids,
                kind=AssessmentNotification.Kind.ASSIGNED,
            )
        )
        return queue_notification_group(notifications, batch_id)


def send_assessment_publication_notifications(assessment):
    """Create assignment rows and queue a publication email batch."""
    if assessment.is_open_to_all_students:
        assignments = AssignmentService.create_assignments_for_all_students(
            assessment
        )
    else:
        assignments = list(
            assessment.assignments.select_related('assessment', 'student').all()
        )

    return send_assignment_notifications(assignments)


def _process_assessment_publication(assessment_id):
    from .models import Assessment

    assessment = Assessment.objects.get(pk=assessment_id)
    return send_assessment_publication_notifications(assessment)


def queue_assessment_publication_notifications(assessment_id):
    """Prepare assignments and their grouped email outside the request thread."""
    transaction.on_commit(
        lambda: _submit_background_job(_process_assessment_publication, assessment_id)
    )
    return {"status": "queued"}
