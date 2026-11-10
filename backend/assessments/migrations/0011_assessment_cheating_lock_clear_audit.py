from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("assessments", "0010_assessment_assignment_integrity_flags"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="assessmentassignment",
            name="cheating_flag_cleared_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="assessmentassignment",
            name="cheating_flag_cleared_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="assessment_cheating_flags_cleared",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
