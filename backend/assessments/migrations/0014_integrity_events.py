from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('assessments', '0013_speed_breach_events'),
        ('users', '0005_user_integrity_warning_count'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='AssessmentSpeedBreachEvent',
            new_name='AssessmentIntegrityEvent',
        ),
        migrations.AddField(
            model_name='assessmentintegrityevent',
            name='event_type',
            field=models.CharField(
                choices=[
                    ('high_code_writing_speed', 'High code-writing speed'),
                    ('tab_hidden', 'Assessment tab hidden'),
                    ('window_blur', 'Assessment window lost focus'),
                    ('fullscreen_exit', 'Fullscreen exited'),
                ],
                default='high_code_writing_speed',
                max_length=32,
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='assessmentintegrityevent',
            name='speed_wpm',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='assessmentintegrityevent',
            name='sustained_ms',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='assessmentintegrityevent',
            name='assignment',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='integrity_events',
                to='assessments.assessmentassignment',
            ),
        ),
        migrations.AlterField(
            model_name='assessmentintegrityevent',
            name='student',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='integrity_events',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
