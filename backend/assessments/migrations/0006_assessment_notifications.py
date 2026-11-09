import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("assessments", "0005_timing_and_answer_drafts"),
    ]

    operations = [
        migrations.CreateModel(
            name="AssessmentNotification",
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
                (
                    "kind",
                    models.CharField(
                        choices=[
                            ("assigned", "Assignment notice"),
                            ("reminder", "Deadline reminder"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("queued", "Queued"),
                            ("sending", "Sending"),
                            ("sent", "Sent"),
                            ("failed", "Failed"),
                            ("skipped", "Skipped"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("scheduled_for", models.DateTimeField(blank=True, null=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
                ("last_error", models.TextField(blank=True)),
                (
                    "assignment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notifications",
                        to="assessments.assessmentassignment",
                    ),
                ),
            ],
            options={
                "ordering": ["kind"],
                "indexes": [
                    models.Index(
                        fields=["status", "scheduled_for"],
                        name="assess_notif_due_idx",
                    ),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="assessmentnotification",
            constraint=models.UniqueConstraint(
                fields=("assignment", "kind"),
                name="unique_assessment_assignment_notification_kind",
            ),
        ),
    ]
