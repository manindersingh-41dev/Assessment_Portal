import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("assessments", "0006_assessment_notifications"),
    ]

    operations = [
        migrations.AddField(
            model_name="assessmentnotification",
            name="email_batch_id",
            field=models.UUIDField(
                db_index=True,
                default=uuid.uuid4,
                help_text="Identifies the recipients of one grouped assessment email.",
            ),
        ),
    ]
