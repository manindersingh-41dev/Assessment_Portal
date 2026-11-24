from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assessments", "0014_integrity_events"),
    ]

    operations = [
        migrations.AddField(
            model_name="assessmentassignment",
            name="cheating_flag_words_per_second",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="assessmentintegrityevent",
            name="words_per_second",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="assessmentintegrityevent",
            name="event_type",
            field=models.CharField(
                choices=[
                    ("high_code_writing_speed", "High code-writing speed"),
                    ("rapid_code_insertion", "Rapid code insertion"),
                    ("bulk_code_insertion", "Bulk code insertion"),
                    ("tab_hidden", "Assessment tab hidden"),
                    ("window_blur", "Assessment window lost focus"),
                    ("fullscreen_exit", "Fullscreen exited"),
                ],
                max_length=32,
            ),
        ),
    ]
