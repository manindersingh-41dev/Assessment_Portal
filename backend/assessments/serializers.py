"""
Serializers for Assessment Management.

Handles validation and transformation for assessments, assignments, and results.
"""

from rest_framework import serializers
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from .models import (
    Assessment, AssessmentQuestion, StudentBatch,
    AssessmentAssignment, AssessmentResult
)
from questions.models import Question, TestCase


class AssessmentQuestionSnapshotSerializer(serializers.Serializer):
    """Serializer for question snapshot data."""

    id = serializers.UUIDField(read_only=True)
    title = serializers.CharField()
    description = serializers.CharField()
    input_format = serializers.CharField()
    output_format = serializers.CharField()
    constraints = serializers.CharField()
    sample_input = serializers.CharField()
    sample_output = serializers.CharField()
    difficulty = serializers.CharField()
    language = serializers.CharField()


class AssessmentQuestionSerializer(serializers.ModelSerializer):
    """Serializer for assessment questions."""

    question_details = AssessmentQuestionSnapshotSerializer(
        source='get_question_snapshot', read_only=True
    )

    class Meta:
        model = AssessmentQuestion
        fields = [
            'id', 'question', 'question_details',
            'question_order', 'marks', 'is_mandatory', 'show_to_students'
        ]
        read_only_fields = ['id', 'question_details']


class AssessmentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating assessments."""

    questions = AssessmentQuestionSerializer(many=True, required=False, write_only=True)

    class Meta:
        model = Assessment
        fields = [
            'title', 'description', 'instructions',
            'start_datetime', 'end_datetime', 'duration_minutes',
            'total_marks', 'passing_marks',
            'resubmission_policy', 'shuffle_questions',
            'show_results_to_students', 'questions'
        ]

    def validate_start_datetime(self, value):
        """Validate start datetime is in future."""
        if value <= timezone.now():
            raise serializers.ValidationError('Start datetime must be in the future')
        return value

    def validate_end_datetime(self, value):
        """Validate end datetime is after start datetime."""
        start = self.initial_data.get('start_datetime')
        if start:
            try:
                start_dt = timezone.datetime.fromisoformat(start.replace('Z', '+00:00'))
                if value <= start_dt:
                    raise serializers.ValidationError('End datetime must be after start datetime')
            except ValueError:
                pass
        return value

    def validate_duration_minutes(self, value):
        """Validate duration."""
        if value < 1:
            raise serializers.ValidationError('Duration must be at least 1 minute')
        if value > 480:  # 8 hours max
            raise serializers.ValidationError('Duration cannot exceed 480 minutes (8 hours)')
        return value

    def validate_passing_marks(self, value):
        """Validate passing marks."""
        total_marks = self.initial_data.get('total_marks')
        if total_marks and value > int(total_marks):
            raise serializers.ValidationError('Passing marks cannot exceed total marks')
        return value

    def create(self, validated_data):
        """Create assessment with questions."""
        questions_data = validated_data.pop('questions', [])
        request = self.context.get('request')

        with transaction.atomic():
            # Create assessment
            assessment = Assessment.objects.create(
                created_by=request.user if request else None,
                **validated_data
            )

            # Add questions if provided
            for order, q_data in enumerate(questions_data, start=1):
                question = q_data['question']

                # Create snapshot of question
                AssessmentQuestion.objects.create(
                    assessment=assessment,
                    question=question,
                    question_title=question.title,
                    question_description=question.description,
                    question_input_format=question.input_format,
                    question_output_format=question.output_format,
                    question_constraints=question.constraints,
                    question_difficulty=question.difficulty,
                    question_language=question.language,
                    question_order=order,
                    marks=q_data.get('marks', question.total_marks),
                    is_mandatory=q_data.get('is_mandatory', True),
                    show_to_students=q_data.get('show_to_students', True)
                )

        return assessment


class AssessmentUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating assessments."""

    class Meta:
        model = Assessment
        fields = [
            'title', 'description', 'instructions',
            'start_datetime', 'end_datetime', 'duration_minutes',
            'total_marks', 'passing_marks',
            'resubmission_policy', 'shuffle_questions',
            'show_results_to_students', 'status'
        ]

    def validate(self, data):
        """Validate assessment update."""
        instance = self.instance

        # Cannot modify active/published assessments
        if instance.status == Assessment.Status.ACTIVE and instance.is_published:
            if 'start_datetime' in data or 'end_datetime' in data:
                raise serializers.ValidationError(
                    'Cannot change datetime of published active assessments'
                )

        # Check if updating marks would affect existing assignments
        if 'total_marks' in data and instance.assignments.exists():
            raise serializers.ValidationError(
                'Cannot change total marks for assessments with existing assignments'
            )

        return data


class AssessmentDetailSerializer(serializers.ModelSerializer):
    """Serializer for assessment details."""

    created_by_name = serializers.CharField(
        source='created_by.get_full_name', read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    resubmission_policy_display = serializers.CharField(
        source='get_resubmission_policy_display', read_only=True
    )
    questions = AssessmentQuestionSerializer(many=True, read_only=True)
    question_count = serializers.IntegerField(read_only=True)
    assignment_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Assessment
        fields = [
            'id', 'title', 'description', 'instructions',
            'start_datetime', 'end_datetime', 'duration_minutes',
            'total_marks', 'passing_marks', 'status', 'status_display',
            'resubmission_policy', 'resubmission_policy_display',
            'shuffle_questions', 'show_results_to_students', 'is_published',
            'created_by_name', 'created_at', 'updated_at',
            'questions', 'question_count', 'assignment_count'
        ]
        read_only_fields = [
            'id', 'created_by_name', 'created_at', 'updated_at',
            'questions', 'question_count', 'assignment_count'
        ]


class AssessmentListSerializer(serializers.ModelSerializer):
    """Serializer for assessment listing."""

    created_by_name = serializers.CharField(
        source='created_by.get_full_name', read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    question_count = serializers.IntegerField(read_only=True)
    assignment_count = serializers.IntegerField(read_only=True)
    is_active_now = serializers.BooleanField(read_only=True)
    is_started = serializers.BooleanField(read_only=True)
    is_ended = serializers.BooleanField(read_only=True)

    class Meta:
        model = Assessment
        fields = [
            'id', 'title', 'start_datetime', 'end_datetime',
            'duration_minutes', 'total_marks', 'status', 'status_display',
            'is_published', 'created_by_name', 'created_at',
            'question_count', 'assignment_count',
            'is_active_now', 'is_started', 'is_ended'
        ]
        read_only_fields = [
            'id', 'created_by_name', 'created_at', 'question_count',
            'assignment_count', 'is_active_now', 'is_started', 'is_ended'
        ]


class StudentBatchSerializer(serializers.ModelSerializer):
    """Serializer for student batches."""

    student_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = StudentBatch
        fields = [
            'id', 'name', 'description', 'department', 'year',
            'created_at', 'updated_at', 'student_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'student_count']


class AssessmentAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for assessment assignments."""

    assessment_title = serializers.CharField(source='assessment.title', read_only=True)
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    student_email = serializers.CharField(source='student.email', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = AssessmentAssignment
        fields = [
            'id', 'assessment', 'assessment_title', 'student', 'student_name', 'student_email',
            'status', 'status_display', 'assigned_at', 'started_at', 'submitted_at',
            'deadline', 'marks_obtained', 'passed', 'attempt_number',
            'is_active', 'is_overdue'
        ]
        read_only_fields = [
            'id', 'assessment_title', 'student_name', 'student_email',
            'status_display', 'assigned_at', 'started_at', 'submitted_at',
            'is_active', 'is_overdue'
        ]


class AssessmentAssignmentCreateSerializer(serializers.Serializer):
    """Serializer for creating assessment assignments."""

    assessment_id = serializers.UUIDField(required=True)
    student_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        help_text="List of student IDs (assign to specific students)"
    )
    batch_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        help_text="List of batch IDs (assign to batches)"
    )
    deadline = serializers.DateTimeField(
        required=False,
        help_text="Custom deadline (if different from assessment)"
    )

    def validate_assessment_id(self, value):
        """Validate assessment exists and is published."""
        try:
            assessment = Assessment.objects.get(id=value)
            if not assessment.is_published:
                raise serializers.ValidationError('Assessment must be published')
            return value
        except Assessment.DoesNotExist:
            raise serializers.ValidationError('Assessment not found')

    def validate(self, data):
        """Validate assignment creation."""
        student_ids = data.get('student_ids', [])
        batch_ids = data.get('batch_ids', [])

        if not student_ids and not batch_ids:
            raise serializers.ValidationError(
                'Must provide either student_ids or batch_ids'
            )

        # Validate assessment exists
        try:
            assessment = Assessment.objects.get(id=data['assessment_id'])
            data['assessment'] = assessment
        except Assessment.DoesNotExist:
            raise serializers.ValidationError('Assessment not found')

        # Validate deadline
        if 'deadline' in data:
            deadline = data['deadline']
            if deadline < assessment.start_datetime:
                raise serializers.ValidationError(
                    'Deadline cannot be before assessment start'
                )
            if deadline > assessment.end_datetime:
                raise serializers.ValidationError(
                    'Deadline cannot be after assessment end'
                )

        return data


class StudentAssessmentSerializer(serializers.ModelSerializer):
    """Serializer for student view of assessments."""

    assignment_status = serializers.SerializerMethodField()
    assignment_id = serializers.SerializerMethodField()
    can_start = serializers.SerializerMethodField()
    started_at = serializers.SerializerMethodField()
    submitted_at = serializers.SerializerMethodField()
    time_remaining = serializers.SerializerMethodField()

    class Meta:
        model = Assessment
        fields = [
            'id', 'title', 'description', 'instructions',
            'start_datetime', 'end_datetime', 'duration_minutes',
            'total_marks', 'passing_marks',
            'assignment_status', 'assignment_id',
            'can_start', 'started_at', 'submitted_at', 'time_remaining'
        ]

    def get_assignment_status(self, obj):
        """Get assignment status for this student."""
        student = self.context.get('student')
        if not student:
            return None

        try:
            assignment = obj.assignments.get(student=student)
            return assignment.status
        except AssessmentAssignment.DoesNotExist:
            return 'not_assigned'

    def get_assignment_id(self, obj):
        """Get assignment ID for this student."""
        student = self.context.get('student')
        if not student:
            return None

        try:
            assignment = obj.assignments.get(student=student)
            return assignment.id
        except AssessmentAssignment.DoesNotExist:
            return None

    def get_can_start(self, obj):
        """Check if student can start this assessment."""
        student = self.context.get('student')
        if not student:
            return False

        try:
            assignment = obj.assignments.get(student=student)
            return assignment.can_start()
        except AssessmentAssignment.DoesNotExist:
            return False

    def get_started_at(self, obj):
        """Get when student started."""
        student = self.context.get('student')
        if not student:
            return None

        try:
            assignment = obj.assignments.get(student=student)
            return assignment.started_at
        except AssessmentAssignment.DoesNotExist:
            return None

    def get_submitted_at(self, obj):
        """Get when student submitted."""
        student = self.context.get('student')
        if not student:
            return None

        try:
            assignment = obj.assignments.get(student=student)
            return assignment.submitted_at
        except AssessmentAssignment.DoesNotExist:
            return None

    def get_time_remaining(self, obj):
        """Get time remaining for student."""
        student = self.context.get('student')
        if not student:
            return None

        try:
            assignment = obj.assignments.get(student=student)
            deadline = assignment.deadline or obj.end_datetime

            if assignment.status != AssessmentAssignment.Status.STARTED:
                return None

            now = timezone.now()
            if now > deadline:
                return None

            remaining = deadline - now
            return int(remaining.total_seconds())
        except AssessmentAssignment.DoesNotExist:
            return None


class AssessmentResultSerializer(serializers.ModelSerializer):
    """Serializer for assessment results."""

    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    student_email = serializers.CharField(source='student.email', read_only=True)
    assessment_title = serializers.CharField(source='assessment.title', read_only=True)

    class Meta:
        model = AssessmentResult
        fields = [
            'id', 'assessment', 'assessment_title',
            'student', 'student_name', 'student_email',
            'total_marks_obtained', 'percentage', 'passed',
            'attempted_at', 'evaluated_at', 'feedback'
        ]
        read_only_fields = [
            'id', 'assessment_title', 'student_name', 'student_email',
            'attempted_at', 'evaluated_at'
        ]


class AssessmentStatsSerializer(serializers.Serializer):
    """Serializer for assessment statistics."""

    total_assessments = serializers.IntegerField(read_only=True)
    active_assessments = serializers.IntegerField(read_only=True)
    completed_assessments = serializers.IntegerField(read_only=True)
    upcoming_assessments = serializers.IntegerField(read_only=True)
    total_assignments = serializers.IntegerField(read_only=True)
    completed_assignments = serializers.IntegerField(read_only=True)
    pending_assignments = serializers.IntegerField(read_only=True)
    average_score = serializers.FloatField(read_only=True)
    pass_rate = serializers.FloatField(read_only=True)


class AssessmentPublishSerializer(serializers.Serializer):
    """Serializer for publishing assessments."""

    publish = serializers.BooleanField(required=True)

    def validate(self, data):
        """Validate publishing."""
        assessment = self.context.get('assessment')
        if not assessment:
            raise serializers.ValidationError('Assessment context required')

        if data['publish'] and assessment.status != Assessment.Status.ACTIVE:
            raise serializers.ValidationError(
                'Assessment must be active before publishing'
            )

        # Check if assessment has questions
        if data['publish'] and not assessment.questions.exists():
            raise serializers.ValidationError(
                'Assessment must have at least one question'
            )

        # Check if total marks match sum of question marks
        if data['publish']:
            total_question_marks = sum(
                q.marks for q in assessment.questions.all()
            )
            if total_question_marks != assessment.total_marks:
                raise serializers.ValidationError(
                    f'Total question marks ({total_question_marks}) '
                    f'must equal assessment marks ({assessment.total_marks})'
                )

        return data
