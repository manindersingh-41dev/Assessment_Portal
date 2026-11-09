from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("submissions", "0004_testcaseverdict_expected_output"),
    ]

    operations = [
        migrations.AddField(
            model_name="codesubmission",
            name="evaluation_generation",
            field=models.PositiveIntegerField(
                default=1,
                help_text="Generation token used to ignore stale or superseded evaluation tasks.",
            ),
        ),
    ]
