from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assessments", "0011_assessment_cheating_lock_clear_audit"),
    ]

    operations = [
        migrations.AddField(
            model_name="assessmentassignment",
            name="cheating_flag_sustained_ms",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
