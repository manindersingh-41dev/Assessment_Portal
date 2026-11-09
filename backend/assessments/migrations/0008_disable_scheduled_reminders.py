from django.db import migrations


def retire_old_notifications(apps, schema_editor):
    notification = apps.get_model("assessments", "AssessmentNotification")

    notification.objects.filter(
        kind="reminder",
        status__in=["pending", "queued", "sending"],
    ).update(
        status="skipped",
        scheduled_for=None,
        last_error="Scheduled assessment reminders have been disabled.",
    )

    notification.objects.filter(
        kind="assigned",
        status__in=["pending", "queued", "sending"],
    ).update(
        status="failed",
        scheduled_for=None,
        last_error=(
            "Delivery from the previous background queue was not confirmed. "
            "Retry this email to send it synchronously."
        ),
    )


class Migration(migrations.Migration):

    dependencies = [
        ("assessments", "0007_group_assessment_emails"),
    ]

    operations = [
        migrations.RunPython(retire_old_notifications, migrations.RunPython.noop),
    ]
