from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_faculty_assessment_timer_preference'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='speed_warning_count',
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text='Lifetime count of sustained code-writing speed warnings given to this student.',
            ),
        ),
    ]
