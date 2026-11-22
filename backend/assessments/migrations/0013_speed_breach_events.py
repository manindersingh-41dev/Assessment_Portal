import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('assessments', '0012_assessment_cheating_flag_sustained_duration'),
        ('users', '0004_user_speed_warning_count'),
    ]

    operations = [
        migrations.CreateModel(
            name='AssessmentSpeedBreachEvent',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('event_id', models.UUIDField()),
                ('speed_wpm', models.FloatField()),
                ('sustained_ms', models.PositiveIntegerField()),
                ('outcome', models.CharField(choices=[('warning', 'Warning'), ('locked', 'Coding window locked')], max_length=12)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('assignment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='speed_breach_events', to='assessments.assessmentassignment')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='speed_breach_events', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='assessmentspeedbreachevent',
            constraint=models.UniqueConstraint(fields=('student', 'event_id'), name='uq_student_speed_event'),
        ),
        migrations.AddIndex(
            model_name='assessmentspeedbreachevent',
            index=models.Index(fields=['student', 'outcome'], name='ix_speed_evt_student_outcome'),
        ),
    ]
