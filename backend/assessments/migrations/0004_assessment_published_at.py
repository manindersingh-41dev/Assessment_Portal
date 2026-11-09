from django.db import migrations, models
from django.db.models import F


def backfill_published_at(apps, schema_editor):
    Assessment = apps.get_model("assessments", "Assessment")
    database = schema_editor.connection.alias
    Assessment.objects.using(database).filter(
        is_published=True,
        published_at__isnull=True,
    ).update(published_at=F("updated_at"))


class Migration(migrations.Migration):
    dependencies = [
        ("assessments", "0003_rename_modified_at_assessment_updated_at_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="assessment",
            name="published_at",
            field=models.DateTimeField(
                blank=True,
                db_index=True,
                help_text="When the assessment was first published.",
                null=True,
                verbose_name="published at",
            ),
        ),
        migrations.RunPython(
            backfill_published_at,
            migrations.RunPython.noop,
        ),
    ]
