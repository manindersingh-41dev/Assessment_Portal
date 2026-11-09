"""
StudentBatch model for Assessment Management.

A batch or class of students used for bulk assessment assignment.
"""

import uuid
from django.db import models
from django.conf import settings

from users.models.base import TimeStampedModel, UUIDModel


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
