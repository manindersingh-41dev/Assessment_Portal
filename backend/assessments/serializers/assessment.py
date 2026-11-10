"""Serializers for assessment management and student assignments."""

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from assessments.models import (
    Assessment,
    AssessmentAnswerDraft,
    AssessmentAssignment,
    AssessmentQuestion,
    AssessmentNotification,
)
from questions.models import Question


class AssessmentQuestionPromptSerializer(serializers.ModelSerializer):
    """Student-safe question prompt included when an assessment is opened."""

    class Meta:
        model = Question
        fields = [
            "id",
            "title",
            "description",
            "input_format",
            "output_format",
            "constraints",
            "sample_input",
            "sample_output",
            "difficulty",
            "language",
            "time_limit_seconds",
            "memory_limit_mb",
        ]
        read_only_fields = fields


class AssessmentQuestionSerializer(serializers.ModelSerializer):
    """Read representation of a question included in an assessment."""

    question_title = serializers.CharField(source="question.title", read_only=True)
    question_difficulty = serializers.CharField(
        source="question.difficulty", read_only=True
    )
    question_details = AssessmentQuestionPromptSerializer(
        source="question", read_only=True
    )

    class Meta:
        model = AssessmentQuestion
        fields = [
            "id",
            "assessment",
            "question",
            "question_title",
            "question_difficulty",
            "question_details",
            "order",
            "marks",
        ]
        read_only_fields = fields


class AssessmentQuestionInputSerializer(serializers.Serializer):
    """Validate a question and its assessment-specific mark value."""

    question = serializers.PrimaryKeyRelatedField(queryset=Question.objects.all())
    marks = serializers.IntegerField(min_value=1, max_value=100)
    order = serializers.IntegerField(min_value=1, required=False)

    def validate_question(self, question):
        request = self.context.get("request")
        if request and question.created_by_id != request.user.id:
            raise serializers.ValidationError(
                "You can only add questions from your question bank."
            )
        return question


class AssessmentSerializer(serializers.ModelSerializer):
    """List representation of an assessment."""

    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)
    assessment_questions = AssessmentQuestionSerializer(many=True, read_only=True)
    question_count = serializers.IntegerField(read_only=True)
    assignment_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Assessment
        fields = [
            "id",
            "title",
            "description",
            "status",
            "start_time",
            "end_time",
            "duration_minutes",
            "is_timed",
            "total_marks",
            "instructions",
            "is_published",
            "is_open_to_all_students",
            "published_at",
            "created_by",
            "created_by_email",
            "assessment_questions",
            "question_count",
            "assignment_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class AssessmentCreateUpdateSerializer(serializers.ModelSerializer):
    """Create or update an assessment together with its selected questions."""

    is_open_to_all_students = serializers.BooleanField(required=False)
    questions = AssessmentQuestionInputSerializer(many=True, required=False)

    class Meta:
        model = Assessment
        fields = [
            "id",
            "title",
            "description",
            "status",
            "start_time",
            "end_time",
            "duration_minutes",
            "is_timed",
            "total_marks",
            "instructions",
            "is_published",
            "is_open_to_all_students",
            "questions",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        if (
            self.instance
            and (self.instance.is_published or self.instance.published_at)
            and "is_open_to_all_students" in attrs
            and attrs["is_open_to_all_students"]
            != self.instance.is_open_to_all_students
        ):
            raise serializers.ValidationError(
                {
                    "is_open_to_all_students": (
                        "Student access cannot be changed after publication."
                    )
                }
            )

        start_time = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end_time = attrs.get("end_time", getattr(self.instance, "end_time", None))
        if start_time and end_time and end_time <= start_time:
            raise serializers.ValidationError(
                {"end_time": "End time must be after start time."}
            )

        questions = attrs.get("questions")
        if self.instance is None and not questions:
            raise serializers.ValidationError(
                {"questions": "Add at least one question to the assessment."}
            )
        if questions is not None:
            question_ids = [item["question"].id for item in questions]
            if len(question_ids) != len(set(question_ids)):
                raise serializers.ValidationError(
                    {"questions": "A question can only be added once."}
                )
            orders = [item.get("order", index + 1) for index, item in enumerate(questions)]
            if len(orders) != len(set(orders)):
                raise serializers.ValidationError(
                    {"questions": "Question order values must be unique."}
                )
            total_marks = sum(item["marks"] for item in questions)
            if total_marks > 1000:
                raise serializers.ValidationError(
                    {"questions": "Assessment total marks cannot exceed 1,000."}
                )
            attrs["total_marks"] = total_marks

        return attrs

    @staticmethod
    def _replace_questions(assessment, questions):
        assessment.assessment_questions.all().delete()
        links = []
        for index, item in enumerate(questions, start=1):
            links.append(
                AssessmentQuestion(
                    assessment=assessment,
                    question=item["question"],
                    marks=item["marks"],
                    order=item.get("order", index),
                )
            )
        AssessmentQuestion.objects.bulk_create(links)

    @transaction.atomic
    def create(self, validated_data):
        questions = validated_data.pop("questions", [])
        if validated_data.get("is_published") and not validated_data.get("published_at"):
            validated_data["published_at"] = timezone.now()
        assessment = super().create(validated_data)
        self._replace_questions(assessment, questions)
        if assessment.is_published:
            from assessments.notifications import send_assessment_publication_notifications

            transaction.on_commit(
                lambda: send_assessment_publication_notifications(assessment)
            )
        return assessment

    @transaction.atomic
    def update(self, instance, validated_data):
        questions = validated_data.pop("questions", None)
        was_published = instance.is_published
        assessment = super().update(instance, validated_data)
        if assessment.is_published and assessment.published_at is None:
            assessment.published_at = timezone.now()
            assessment.save(update_fields=["published_at", "updated_at"])
        if questions is not None:
            self._replace_questions(assessment, questions)
        if assessment.is_published and not was_published:
            from assessments.notifications import send_assessment_publication_notifications

            transaction.on_commit(
                lambda: send_assessment_publication_notifications(assessment)
            )
        return assessment


class AssessmentDetailSerializer(AssessmentSerializer):
    """Detailed representation retained for student and faculty pages."""

    questions = AssessmentQuestionSerializer(
        many=True, read_only=True, source="assessment_questions"
    )

    class Meta(AssessmentSerializer.Meta):
        fields = AssessmentSerializer.Meta.fields + ["questions"]


class AssessmentAssignmentSerializer(serializers.ModelSerializer):
    """Read representation of an assessment assignment."""

    student_email = serializers.EmailField(source="student.email", read_only=True)
    student_name = serializers.CharField(
        source="student.get_full_name", read_only=True
    )
    assessment_title = serializers.CharField(source="assessment.title", read_only=True)
    email_notifications = serializers.SerializerMethodField()

    def get_email_notifications(self, assignment):
        request = self.context.get("request")
        if not request or getattr(request.user, "role", None) != "faculty":
            return []
        notifications = assignment.notifications.filter(
            kind=AssessmentNotification.Kind.ASSIGNED
        )
        return AssessmentNotificationSerializer(notifications, many=True).data

    class Meta:
        model = AssessmentAssignment
        fields = [
            "id",
            "assessment",
            "assessment_title",
            "student",
            "student_name",
            "student_email",
            "status",
            "started_at",
            "submitted_at",
            "due_at",
            "is_flagged_cheating",
            "cheating_flag_reason",
            "cheating_flag_speed_wpm",
            "cheating_flag_sustained_ms",
            "cheating_flagged_at",
            "cheating_flag_cleared_at",
            "cheating_flag_cleared_by",
            "created_at",
            "updated_at",
            "email_notifications",
        ]
        read_only_fields = fields


class AssessmentNotificationSerializer(serializers.ModelSerializer):
    """Read-only email delivery status visible to the assessment's faculty."""

    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    recipient_count = serializers.SerializerMethodField()

    def get_recipient_count(self, notification):
        cache = self.context.setdefault("email_batch_recipient_counts", {})
        key = (str(notification.email_batch_id), notification.kind)
        if key not in cache:
            cache[key] = AssessmentNotification.objects.filter(
                email_batch_id=notification.email_batch_id,
                kind=notification.kind,
            ).exclude(status=AssessmentNotification.Status.SKIPPED).count()
        return cache[key]

    class Meta:
        model = AssessmentNotification
        fields = [
            "id", "kind", "kind_display", "status", "status_display",
            "scheduled_for", "sent_at", "attempts", "last_error",
            "recipient_count",
        ]
        read_only_fields = fields


class AssessmentAnswerDraftSerializer(serializers.ModelSerializer):
    """Read representation of an autosaved answer draft."""

    question_id = serializers.UUIDField(
        source="assessment_question_id",
        read_only=True,
    )

    class Meta:
        model = AssessmentAnswerDraft
        fields = ["question_id", "source_code", "updated_at"]
        read_only_fields = fields


class AssessmentAnswerDraftWriteSerializer(serializers.Serializer):
    """Validate an autosave request from the assigned student."""

    question_id = serializers.UUIDField()
    source_code = serializers.CharField(max_length=100000, allow_blank=True)


class AssessmentAssignmentCreateSerializer(serializers.Serializer):
    """Validate individual and batch assignment requests."""

    student_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, allow_empty=True
    )
    batch_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, allow_empty=True
    )
    deadline = serializers.DateTimeField(required=False, allow_null=True)
