"""Shared question identity and duplicate-content validation."""

QUESTION_CONTENT_FIELDS = (
    "title",
    "description",
    "input_format",
    "output_format",
    "constraints",
)


def normalize_question_text(value):
    return " ".join((value or "").split()).casefold()


def question_content_fingerprint(values):
    return tuple(
        normalize_question_text(values.get(field, ""))
        for field in QUESTION_CONTENT_FIELDS
    )


def find_duplicate_question(values, exclude_id=None):
    """Find an existing question with the same normalized problem statement."""
    from questions.models import Question

    title = (values.get("title") or "").strip()
    if not title:
        return None

    candidates = Question.objects.filter(title__iexact=title)
    if exclude_id is not None:
        candidates = candidates.exclude(pk=exclude_id)

    fingerprint = question_content_fingerprint(values)
    for candidate in candidates.only("id", *QUESTION_CONTENT_FIELDS).iterator():
        candidate_values = {field: getattr(candidate, field) for field in QUESTION_CONTENT_FIELDS}
        if question_content_fingerprint(candidate_values) == fingerprint:
            return candidate
    return None
