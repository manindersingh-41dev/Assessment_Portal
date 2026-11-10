from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assessments", "0008_disable_scheduled_reminders"),
    ]

    operations = [
        # Preserve the old restricted behavior for assessments already in the database.
        migrations.AddField(
            model_name="assessment",
            name="is_open_to_all_students",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "When published, any registered student can see and attempt "
                    "this assessment. Turn off to restrict access to assigned students."
                ),
                verbose_name="open to all students",
            ),
        ),
        migrations.AlterField(
            model_name="assessment",
            name="is_open_to_all_students",
            field=models.BooleanField(
                default=True,
                help_text=(
                    "When published, any registered student can see and attempt "
                    "this assessment. Turn off to restrict access to assigned students."
                ),
                verbose_name="open to all students",
            ),
        ),
        migrations.AddIndex(
            model_name="assessment",
            index=models.Index(
                fields=["is_published", "is_open_to_all_students"],
                name="assessment_public_students_idx",
            ),
        ),
    ]
