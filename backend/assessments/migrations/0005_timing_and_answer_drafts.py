import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("assessments", "0004_assessment_published_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="assessment",
            name="is_timed",
            field=models.BooleanField(
                default=True,
                help_text="Whether students must complete the assessment within duration_minutes.",
                verbose_name="timed assessment",
            ),
        ),
        migrations.CreateModel(
            name="AssessmentAnswerDraft",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("source_code", models.TextField()),
                (
                    "assessment_question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="answer_drafts",
                        to="assessments.assessmentquestion",
                    ),
                ),
                (
                    "assignment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="answer_drafts",
                        to="assessments.assessmentassignment",
                    ),
                ),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.AddConstraint(
            model_name="assessmentanswerdraft",
            constraint=models.UniqueConstraint(
                fields=("assignment", "assessment_question"),
                name="unique_assignment_question_draft",
            ),
        ),
    ]
