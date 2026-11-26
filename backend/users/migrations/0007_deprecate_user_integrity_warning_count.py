from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0006_user_active_session_id"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="integrity_warning_count",
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text="Deprecated; integrity warnings are now counted per assessment assignment.",
            ),
        ),
    ]
