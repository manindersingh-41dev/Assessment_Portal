from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assessments", "0015_code_insertion_rate_integrity_events"),
    ]

    operations = [
        migrations.AddField(
            model_name="assessmentassignment",
            name="integrity_warning_count",
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text="Integrity warnings recorded during this assessment assignment.",
            ),
        ),
    ]
