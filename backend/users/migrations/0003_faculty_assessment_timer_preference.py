from django.db import migrations, models


def seed_preference_from_latest_assessment(apps, schema_editor):
    FacultyProfile = apps.get_model('users', 'FacultyProfile')
    Assessment = apps.get_model('assessments', 'Assessment')
    database = schema_editor.connection.alias

    profiles = FacultyProfile.objects.using(database).all().iterator()
    for profile in profiles:
        latest_preference = (
            Assessment.objects.using(database)
            .filter(created_by_id=profile.user_id)
            .order_by('-updated_at', '-created_at')
            .values_list('is_timed', flat=True)
            .first()
        )
        if latest_preference is not None:
            FacultyProfile.objects.using(database).filter(pk=profile.pk).update(
                default_assessment_is_timed=latest_preference,
            )


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0002_emailotp_loginattempt_alter_facultyprofile_options_and_more'),
        ('assessments', '0007_group_assessment_emails'),
    ]

    operations = [
        migrations.AddField(
            model_name='facultyprofile',
            name='default_assessment_is_timed',
            field=models.BooleanField(
                default=True,
                help_text='Default timer setting for new assessments created by this faculty member.',
            ),
        ),
        migrations.RunPython(
            seed_preference_from_latest_assessment,
            migrations.RunPython.noop,
        ),
    ]
