"""Autosaved source code for an in-progress assessment question."""

from django.db import models

from users.models.base import TimeStampedModel, UUIDModel


class AssessmentAnswerDraft(UUIDModel, TimeStampedModel):
    """The latest unsent code for one question in a student's assignment."""

    assignment = models.ForeignKey(
        "assessments.AssessmentAssignment",
        on_delete=models.CASCADE,
        related_name="answer_drafts",
    )
    assessment_question = models.ForeignKey(
        "assessments.AssessmentQuestion",
        on_delete=models.CASCADE,
        related_name="answer_drafts",
    )
    source_code = models.TextField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["assignment", "assessment_question"],
                name="unique_assignment_question_draft",
            ),
        ]
        ordering = ["created_at"]

    def __str__(self):
        return f"Draft for {self.assignment_id} / {self.assessment_question_id}"
