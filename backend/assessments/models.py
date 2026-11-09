"""
Assessment Management Models for Geeta University Coding Assessment Portal.

Implements assessments, assignments, and assessment questions with versioning.
"""

import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import timedelta

from users.models.base import CreatedByModel, TimeStampedModel, UUIDModel


class Assessment(UUIDModel, TimeStampedModel, CreatedByModel):
    """
    An assessment containing one or more coding questions.

    Faculty create assessments with questions, then assign them to students.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"

    class ResubmissionPolicy(models.TextChoices):
        NOT_ALLOWED = "not_allowed", "Not Allowed"
        ONCE = "once", "Once"
        UNLIMITED = "unlimited", "Unlimited"

    # Basic information
    title = models.CharField(
        max_length=200,
        db_index=True,
        help_text="Assessment title"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Assessment description"
    )
    instructions = models.TextField(
        blank=True,
        null=True,
        help_text="Assessment instructions for students"
    )

    # Timing
    start_datetime = models.DateTimeField(
        help_text="When assessment becomes available"
    )
    end_datetime = models.DateTimeField(
        help_text="When assessment closes"
    )
    duration_minutes = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(480)],
        help_text="Duration in minutes (1-480)"
    )

    # Marks
    total_marks = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(1000)],
        help_text="Total marks for assessment"
    )
    passing_marks = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(1000)],
        help_text="Minimum marks to pass"
    )

    # Configuration
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        help_text="Draft, Active, or Archived"
    )
    resubmission_policy = models.CharField(
        max_length=20,
        choices=ResubmissionPolicy.choices,
        default=ResubmissionPolicy.NOT_ALLOWED,
        help_text="Allow students to resubmit"
    )
    shuffle_questions = models.BooleanField(
        default=False,
        help_text="Show questions in random order to students"
    )
    show_results_to_students = models.BooleanField(
        default=False,
        help_text="Show results to students after assessment"
    )
    is_published = models.BooleanField(
        default=False,
        help_text="Published to students"
    )

    class Meta:
        db_table = "assessments_assessment"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_by"], name="ass_status_createdby_idx"),
            models.Index(fields=["start_datetime", "end_datetime"], name="ass_datetime_idx"),
            models.Index(fields=["is_published"], name="ass_published_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                name="assessment_start_before_end",
                condition=models.Q(start_datetime__lt=models.F("end_datetime"))
            ),
            models.CheckConstraint(
                name="assessment_passing_less_equal_total",
                condition=models.Q(passing_marks__lte=models.F("total_marks"))
            ),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    @property
    def is_active_now(self):
        """Check if assessment is currently active."""
        now = timezone.now()
        return self.start_datetime <= now <= self.end_datetime

    @property
    def is_started(self):
        """Check if assessment has started."""
        return timezone.now() >= self.start_datetime

    @property
    def is_ended(self):
        """Check if assessment has ended."""
        return timezone.now() > self.end_datetime

    @property
    def question_count(self):
        """Get number of questions in assessment."""
        return self.questions.count()

    def can_start_now(self):
        """Check if assessment can be started right now."""
        return self.is_started and not self.is_ended


class AssessmentQuestion(UUIDModel, TimeStampedModel):
    """
    Through model linking Assessment to Question with ordering and versioning.

    Stores a snapshot of question at the time of assignment to preserve
    the assessment even if the original question is later modified.
    """

    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.CASCADE,
        related_name="questions",
        help_text="Assessment containing this question"
    )
    question = models.ForeignKey(
        "questions.Question",
        on_delete=models.PROTECT,
        related_name="assessments",
        help_text="Original question from question bank"
    )

    # Question snapshot (for versioning)
    question_title = models.CharField(max_length=200)
    question_description = models.TextField()
    question_input_format = models.TextField()
    question_output_format = models.TextField()
    question_constraints = models.TextField()
    question_difficulty = models.CharField(max_length=20)
    question_language = models.CharField(max_length=20, default="c")

    # Assessment-specific settings
    question_order = models.PositiveIntegerField(
        help_text="Position in assessment (1-based)"
    )
    marks = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text="Marks for this question in this assessment"
    )
    is_mandatory = models.BooleanField(
        default=True,
        help_text="Must be attempted"
    )
    show_to_students = models.BooleanField(
        default=True,
        help_text="Visible to students"
    )

    class Meta:
        db_table = "assessments_assessmentquestion"
        unique_together = [["assessment", "question_order"]]
        ordering = ["question_order"]
        indexes = [
            models.Index(fields=["assessment", "question_order"], name="assq_ass_order_idx"),
        ]

    def __str__(self):
        return f"{self.assessment.title} - Q{self.question_order}: {self.question_title}"


class StudentBatch(UUIDModel, TimeStampedModel):
    """
    A batch or class of students.

    Used for bulk assessment assignment.
    """

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    year = models.IntegerField(
        choices=[(i, f'Year {i}') for i in range(1, 5)],
        blank=True,
        null=True
    )
    students = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="batches",
        limit_choices_to={"role": "student"}
    )

    class Meta:
        db_table = "assessments_studentbatch"
        ordering = ["name"]

    def __str__(self):
        return self.name


class AssessmentAssignment(UUIDModel, TimeStampedModel):
    """
    Assignment of an assessment to a student or group of students.

    Tracks when assignment was given, started, and submitted.
    """

    class Status(models.TextChoices):
        ASSIGNED = "assigned", "Assigned"
        STARTED = "started", "Started"
        SUBMITTED = "submitted", "Submitted"
        EVALUATED = "evaluated", "Evaluated"

    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.CASCADE,
        related_name="assignments",
        help_text="Assessment assigned"
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assessment_assignments",
        limit_choices_to={"role": "student"},
        help_text="Student assigned this assessment"
    )

    # Assignment timestamps
    assigned_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    # Deadline can be different from assessment end time
    deadline = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Custom deadline for this student (if different from assessment)"
    )

    # Status and results
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ASSIGNED,
        db_index=True
    )
    marks_obtained = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Marks obtained (after evaluation)"
    )
    passed = models.BooleanField(
        null=True,
        blank=True,
        help_text="Whether student passed (marks >= passing_marks)"
    )

    # Resubmission tracking
    attempt_number = models.PositiveIntegerField(default=1)
    last_attempt_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "assessments_assessmentassignment"
        unique_together = [["assessment", "student", "attempt_number"]]
        ordering = ["-assigned_at"]
        indexes = [
            models.Index(fields=["student", "status"], name="assass_student_status_idx"),
            models.Index(fields=["assessment", "student"], name="assass_ass_student_idx"),
        ]

    def __str__(self):
        return f"{self.assessment.title} - {self.student.email}"

    @property
    def is_active(self):
        """Check if assignment is currently active."""
        now = timezone.now()
        deadline = self.deadline or self.assessment.end_datetime
        return self.status in [self.Status.ASSIGNED, self.Status.STARTED] and now <= deadline

    @property
    def is_overdue(self):
        """Check if assignment is overdue."""
        now = timezone.now()
        deadline = self.deadline or self.assessment.end_datetime
        return now > deadline and self.status != self.Status.SUBMITTED

    def can_start(self):
        """Check if student can start this assignment."""
        if self.status == self.Status.SUBMITTED:
            # Check resubmission policy
            if self.assessment.resubmission_policy == Assessment.ResubmissionPolicy.NOT_ALLOWED:
                return False
            elif self.assessment.resubmission_policy == Assessment.ResubmissionPolicy.ONCE:
                return self.attempt_number == 1

        now = timezone.now()
        deadline = self.deadline or self.assessment.end_datetime

        # Must be after start time and before deadline
        return self.assessment.start_datetime <= now <= deadline

    def mark_started(self):
        """Mark assignment as started."""
        self.status = self.Status.STARTED
        self.started_at = timezone.now()
        self.save()

    def mark_submitted(self):
        """Mark assignment as submitted."""
        self.status = self.Status.SUBMITTED
        self.submitted_at = timezone.now()
        self.last_attempt_at = timezone.now()
        self.save()


class AssessmentResult(UUIDModel, TimeStampedModel):
    """
    Final result of an assessment for a student.

    Links to assessment and student with final marks.
    """

    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.CASCADE,
        related_name="results",
        help_text="Assessment"
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assessment_results",
        limit_choices_to={"role": "student"},
        help_text="Student"
    )

    total_marks_obtained = models.PositiveIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(1000)]
    )
    percentage = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    passed = models.BooleanField(help_text="Whether student passed")

    attempted_at = models.DateTimeField()
    evaluated_at = models.DateTimeField(auto_now_add=True)

    # Optional feedback
    feedback = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "assessments_assessmentresult"
        unique_together = [["assessment", "student"]]
        ordering = ["-evaluated_at"]
        indexes = [
            models.Index(fields=["student"], name="asres_student_idx"),
        ]

    def __str__(self):
        return f"{self.assessment.title} - {self.student.email}: {self.total_marks_obtained}/{self.assessment.total_marks}"
