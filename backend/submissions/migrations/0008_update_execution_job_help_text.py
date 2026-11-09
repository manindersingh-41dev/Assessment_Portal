from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("submissions", "0007_client_evaluation_case_snapshot"),
    ]

    operations = [
        migrations.AlterField(
            model_name="codesubmission",
            name="execution_job_id",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="Background execution job ID, when available.",
                max_length=100,
                null=True,
                unique=True,
            ),
        ),
    ]
