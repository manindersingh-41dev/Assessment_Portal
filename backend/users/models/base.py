"""
Base models for Geeta University Coding Assessment Portal.

Provides abstract base classes for common model patterns:
- UUIDModel: UUID primary key
- TimeStampedModel: Audit timestamps
- CreatedByModel: Track user who created record
"""

import uuid
from django.db import models
from django.conf import settings


class UUIDModel(models.Model):
    """Abstract model with UUID primary key."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    """Abstract model with creation and modification timestamps."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class CreatedByModel(models.Model):
    """Abstract model tracking the user who created the record."""

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User who created this record.",
        related_name='%(class)s_created'
    )

    class Meta:
        abstract = True
