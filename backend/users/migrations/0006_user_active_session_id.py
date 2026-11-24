import uuid

from django.db import migrations, models


def invalidate_existing_student_sessions(apps, schema_editor):
    User = apps.get_model("users", "User")
    for user in User.objects.filter(role="student", active_session_id__isnull=True).iterator():
        User.objects.filter(pk=user.pk).update(active_session_id=uuid.uuid4())


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0005_user_integrity_warning_count"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="active_session_id",
            field=models.UUIDField(
                blank=True,
                editable=False,
                help_text="Current student session; a new login invalidates older student tokens.",
                null=True,
            ),
        ),
        migrations.RunPython(
            invalidate_existing_student_sessions,
            migrations.RunPython.noop,
        ),
    ]
