from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assessments", "0009_assessment_open_to_all_students"),
    ]

    operations = [
        migrations.AddField(
            model_name="assessmentassignment",
            name="is_flagged_cheating",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text="Whether an integrity rule flagged this assessment attempt.",
            ),
        ),
        migrations.AddField(
            model_name="assessmentassignment",
            name="cheating_flag_reason",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="assessmentassignment",
            name="cheating_flag_speed_wpm",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="assessmentassignment",
            name="cheating_flagged_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
