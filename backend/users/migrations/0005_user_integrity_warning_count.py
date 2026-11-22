from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_user_speed_warning_count'),
    ]

    operations = [
        migrations.RenameField(
            model_name='user',
            old_name='speed_warning_count',
            new_name='integrity_warning_count',
        ),
        migrations.AlterField(
            model_name='user',
            name='integrity_warning_count',
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text='Lifetime count of integrity warnings given to this student.',
            ),
        ),
    ]
