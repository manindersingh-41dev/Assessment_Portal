from django.db import migrations, models


def populate_visible_expected_output(apps, schema_editor):
    TestCaseVerdict = apps.get_model("submissions", "TestCaseVerdict")
    QuestionTestCase = apps.get_model("questions", "TestCase")
    database = schema_editor.connection.alias

    verdicts = TestCaseVerdict.objects.using(database).filter(
        is_sample=True
    ).select_related("submission__question")

    for verdict in verdicts.iterator():
        assessment_question = verdict.submission.question
        expected_output = QuestionTestCase.objects.using(database).filter(
            question_id=assessment_question.question_id,
            order=verdict.test_case_order,
            is_sample=True,
        ).values_list("expected_output", flat=True).first()
        if expected_output is not None:
            TestCaseVerdict.objects.using(database).filter(pk=verdict.pk).update(
                expected_output=expected_output
            )


class Migration(migrations.Migration):
    dependencies = [
        ("questions", "0003_question_fields_and_timestamps"),
        ("submissions", "0003_codesubmission_executionlog_testcaseverdict_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="testcaseverdict",
            name="expected_output",
            field=models.TextField(
                blank=True,
                help_text="Expected output for visible test cases",
                null=True,
            ),
        ),
        migrations.RunPython(
            populate_visible_expected_output,
            migrations.RunPython.noop,
        ),
    ]
