"""
Submission model.

A student submits a C program for a question within an assessment assignment.
The submission carries the source code, language, overall status, and the
marks obtained. It is linked to one assignment and one question.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from users.models.base import TimeStampedModel, UUIDModel


class Submission(UUIDModel, TimeStampedModel):
    """
    A student's submission of source code for a question in an assessment.

    ``code`` is the submitted C source. ``language`` identifies the language
    (currently C). ``status`` tracks the submission lifecycle
    (pending -> compiling/running -> completed/failed). ``marks_obtained`` is
    the total marks awarded after test-case evaluation.
    """

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        COMPILING = "compiling", _("Compiling")
        RUNNING = "running", _("Running")
        COMPLETED = "completed", _("Completed")
        FAILED = "failed", _("Failed")
        COMPILE_ERROR = "compile_error", _("Compile Error")

    class Language(models.TextChoices):
        C = "c", _("C")

    assignment = models.ForeignKey(
        "assessments.AssessmentAssignment",
        on_delete=models.CASCADE,
        related_name="submissions",
        help_text="The assessment assignment this submission belongs to.",
    )
    question = models.ForeignKey(
        "questions.Question",
        on_delete=models.CASCADE,
        related_name="submissions",
        help_text="The question being answered.",
    )
    student = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="submissions",
        limit_choices_to={"role": "student"},
        help_text="The student who made this submission.",
    )
    code = models.TextField(
        _("code"), help_text="The submitted C source code."
    )
    language = models.CharField(
        _("language"),
        max_length=20,
        choices=Language.choices,
        default=Language.C,
    )
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    marks_obtained = models.PositiveSmallIntegerField(
        _("marks obtained"),
        default=0,
        help_text="Total marks awarded after test-case evaluation.",
    )
    compile_output = models.TextField(
        _("compile output"),
        blank=True,
        help_text="Compiler output / errors, if any.",
    )
    executed_at = models.DateTimeField(
        _("executed at"),
        null=True,
        blank=True,
        help_text="When the submission finished execution/evaluation.",
    )

    class Meta:
        verbose_name = _("submission")
        verbose_name_plural = _("submissions")
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["student", "status"], name="submission_student_status_idx"
            ),
            models.Index(
                fields=["assignment", "question"],
                name="submission_ass_q_idx",
            ),
            models.Index(fields=["status"], name="submission_status_idx"),
            models.Index(fields=["created_at"], name="submission_created_at_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                name="submission_marks_obtained_non_negative",
                condition=models.Q(marks_obtained__gte=0),
            ),
        ]

    def __str__(self):
        return f"Submission {self.id} by {self.student.email} for {self.question.title}"
