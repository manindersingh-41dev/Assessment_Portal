"""
TestCase model for questions.

Contains sample input/output for a question. Test cases can be marked as
"sample" (visible to students) or hidden (used only during grading).
"""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from users.models.base import TimeStampedModel, UUIDModel


class TestCase(UUIDModel, TimeStampedModel):
    """
    A test case for a question.

    Contains the input given to the program and the expected output. The
    ``is_sample`` flag marks cases shown to students before they submit;
    hidden cases are used only during grading. ``marks`` defines how much of
    the question's total marks this case is worth.
    """

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    question = models.ForeignKey(
        "questions.Question",
        on_delete=models.CASCADE,
        related_name="test_cases",
        help_text="The question this test case belongs to.",
    )
    input = models.TextField(
        _("input"), help_text="Standard input provided to the program."
    )
    expected_output = models.TextField(
        _("expected output"),
        help_text="Expected standard output from the program.",
    )
    is_sample = models.BooleanField(
        _("is sample"),
        default=False,
        help_text="If True, the test case is visible to students before submission.",
    )
    marks = models.PositiveSmallIntegerField(
        _("marks"),
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text="Marks awarded if this test case passes.",
    )
    order = models.PositiveSmallIntegerField(
        _("order"),
        default=0,
        help_text="Execution order of the test case.",
    )

    class Meta:
        verbose_name = _("test case")
        verbose_name_plural = _("test cases")
        ordering = ["order", "created_at"]
        indexes = [
            models.Index(
                fields=["question", "is_sample"], name="test_case_question_sample_idx"
            ),
            models.Index(
                fields=["question", "order"], name="test_case_question_order_idx"
            ),
        ]
        constraints = [
            models.CheckConstraint(
                name="test_case_marks_positive",
                condition=models.Q(marks__gte=1),
            ),
        ]

    def __str__(self):
        return f"TestCase {self.order} for {self.question.title}"
