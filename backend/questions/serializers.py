"""
Serializers for Question Bank Management.

Handles validation and transformation for questions and test cases.
Implements proper faculty permissions and test case validation.
"""

from rest_framework import serializers
from django.db import transaction
from .models import Question, TestCase


class TestCaseSerializer(serializers.ModelSerializer):
    """Serializer for test case creation and updates."""

    class Meta:
        model = TestCase
        fields = [
            'id', 'input', 'expected_output', 'is_sample', 'marks', 'order'
        ]
        read_only_fields = ['id']

    def validate_marks(self, value):
        """Validate marks are positive."""
        if value < 1:
            raise serializers.ValidationError('Marks must be at least 1')
        if value > 100:
            raise serializers.ValidationError('Marks cannot exceed 100')
        return value


class TestCaseDetailSerializer(TestCaseSerializer):
    """Read-only serializer for test case details."""

    pass


class QuestionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new questions."""

    test_cases = TestCaseSerializer(many=True, required=False, write_only=True)

    class Meta:
        model = Question
        fields = [
            'title', 'description', 'input_format', 'output_format',
            'constraints', 'sample_input', 'sample_output', 'sample_explanation',
            'difficulty', 'topic', 'total_marks', 'time_limit_seconds',
            'memory_limit_mb', 'test_cases'
        ]

    def validate_title(self, value):
        """Validate title is not empty."""
        if not value.strip():
            raise serializers.ValidationError('Title cannot be empty')
        return value

    def validate_total_marks(self, value):
        """Validate total marks."""
        if value < 1 or value > 100:
            raise serializers.ValidationError('Total marks must be between 1 and 100')
        return value

    def validate_time_limit_seconds(self, value):
        """Validate time limit."""
        if value < 1:
            raise serializers.ValidationError('Time limit must be at least 1 second')
        if value > 3600:
            raise serializers.ValidationError('Time limit cannot exceed 3600 seconds')
        return value

    def validate_memory_limit_mb(self, value):
        """Validate memory limit."""
        if value < 1:
            raise serializers.ValidationError('Memory limit must be at least 1 MB')
        if value > 2048:
            raise serializers.ValidationError('Memory limit cannot exceed 2048 MB')
        return value

    def validate(self, data):
        """Validate overall question data."""
        test_cases = data.get('test_cases', [])

        if test_cases:
            # Calculate total marks from test cases
            total_test_marks = sum(tc.get('marks', 0) for tc in test_cases)

            if total_test_marks != data['total_marks']:
                raise serializers.ValidationError({
                    'test_cases': f'Total test case marks ({total_test_marks}) must equal total marks ({data["total_marks"]})'
                })

            # Validate at least one sample test case
            has_sample = any(tc.get('is_sample', False) for tc in test_cases)
            if not has_sample:
                raise serializers.ValidationError({
                    'test_cases': 'At least one sample test case is required'
                })

        return data

    def create(self, validated_data):
        """Create question with test cases."""
        test_cases_data = validated_data.pop('test_cases', [])
        user = self.context['request'].user

        with transaction.atomic():
            question = Question.objects.create(
                created_by=user,
                **validated_data
            )

            # Create test cases
            for order, tc_data in enumerate(test_cases_data, start=1):
                TestCase.objects.create(
                    question=question,
                    order=order,
                    **tc_data
                )

        return question


class QuestionUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating existing questions."""

    class Meta:
        model = Question
        fields = [
            'title', 'description', 'input_format', 'output_format',
            'constraints', 'sample_input', 'sample_output', 'sample_explanation',
            'difficulty', 'topic', 'total_marks', 'time_limit_seconds',
            'memory_limit_mb'
        ]

    def validate_title(self, value):
        """Validate title is not empty."""
        if not value.strip():
            raise serializers.ValidationError('Title cannot be empty')
        return value

    def validate_total_marks(self, value):
        """Validate total marks."""
        if value < 1 or value > 100:
            raise serializers.ValidationError('Total marks must be between 1 and 100')
        return value

    def validate_time_limit_seconds(self, value):
        """Validate time limit."""
        if value < 1:
            raise serializers.ValidationError('Time limit must be at least 1 second')
        if value > 3600:
            raise serializers.ValidationError('Time limit cannot exceed 3600 seconds')
        return value

    def validate_memory_limit_mb(self, value):
        """Validate memory limit."""
        if value < 1:
            raise serializers.ValidationError('Memory limit must be at least 1 MB')
        if value > 2048:
            raise serializers.ValidationError('Memory limit cannot exceed 2048 MB')
        return value

    def validate(self, data):
        """Validate question data."""
        instance = self.instance

        # If updating marks, validate against test cases
        if 'total_marks' in data:
            new_marks = data['total_marks']
            test_cases = instance.test_cases.all()

            if test_cases.exists():
                total_test_marks = sum(tc.marks for tc in test_cases)
                if total_test_marks != new_marks:
                    raise serializers.ValidationError({
                        'total_marks': f'Total test case marks ({total_test_marks}) must equal new total marks ({new_marks})'
                    })

        return data


class QuestionDetailSerializer(serializers.ModelSerializer):
    """Serializer for displaying question details with all information."""

    test_cases = TestCaseDetailSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(
        source='created_by.get_full_name', read_only=True
    )
    difficulty_display = serializers.CharField(
        source='get_difficulty_display', read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )

    class Meta:
        model = Question
        fields = [
            'id', 'title', 'description', 'input_format', 'output_format',
            'constraints', 'sample_input', 'sample_output', 'sample_explanation',
            'difficulty', 'difficulty_display', 'topic', 'language',
            'total_marks', 'status', 'status_display', 'time_limit_seconds',
            'memory_limit_mb', 'created_by_name', 'created_at', 'updated_at',
            'test_cases'
        ]
        read_only_fields = [
            'id', 'created_by_name', 'created_at', 'updated_at', 'test_cases'
        ]


class QuestionListSerializer(serializers.ModelSerializer):
    """Serializer for listing questions (summary view)."""

    created_by_name = serializers.CharField(
        source='created_by.get_full_name', read_only=True
    )
    difficulty_display = serializers.CharField(
        source='get_difficulty_display', read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    test_case_count = serializers.SerializerMethodField()
    sample_test_case_count = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = [
            'id', 'title', 'difficulty', 'difficulty_display', 'topic',
            'total_marks', 'status', 'status_display', 'created_by_name',
            'created_at', 'test_case_count', 'sample_test_case_count'
        ]
        read_only_fields = [
            'id', 'created_by_name', 'created_at', 'test_case_count',
            'sample_test_case_count'
        ]

    def get_test_case_count(self, obj):
        """Get total number of test cases."""
        return obj.test_cases.count()

    def get_sample_test_case_count(self, obj):
        """Get number of sample test cases."""
        return obj.test_cases.filter(is_sample=True).count()


class QuestionPreviewSerializer(serializers.ModelSerializer):
    """Serializer for preview before saving (includes validation)."""

    test_cases = TestCaseSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = [
            'title', 'description', 'input_format', 'output_format',
            'constraints', 'sample_input', 'sample_output', 'sample_explanation',
            'difficulty', 'topic', 'total_marks', 'time_limit_seconds',
            'memory_limit_mb', 'test_cases'
        ]

    def validate(self, data):
        """Validate question for preview."""
        test_cases = data.get('test_cases', [])

        if test_cases:
            total_test_marks = sum(tc.get('marks', 0) for tc in test_cases)
            if total_test_marks != data['total_marks']:
                raise serializers.ValidationError({
                    'test_cases': f'Total test case marks ({total_test_marks}) must equal total marks ({data["total_marks"]})'
                })

            has_sample = any(tc.get('is_sample', False) for tc in test_cases)
            if not has_sample:
                raise serializers.ValidationError({
                    'test_cases': 'At least one sample test case is required'
                })

        return data


class QuestionStatusChangeSerializer(serializers.ModelSerializer):
    """Serializer for changing question status."""

    class Meta:
        model = Question
        fields = ['status']

    def validate_status(self, value):
        """Validate status change."""
        if value not in Question.Status.values:
            raise serializers.ValidationError('Invalid status')

        instance = self.instance
        current_status = instance.status

        # Validate status transitions
        valid_transitions = {
            Question.Status.DRAFT: [
                Question.Status.ACTIVE, Question.Status.ARCHIVED
            ],
            Question.Status.ACTIVE: [
                Question.Status.DRAFT, Question.Status.ARCHIVED
            ],
            Question.Status.ARCHIVED: [Question.Status.ACTIVE],
        }

        if value not in valid_transitions.get(current_status, []):
            raise serializers.ValidationError(
                f'Cannot transition from {current_status} to {value}'
            )

        return value


class TestCaseCreateSerializer(serializers.ModelSerializer):
    """Serializer for adding test cases to existing questions."""

    class Meta:
        model = TestCase
        fields = ['input', 'expected_output', 'is_sample', 'marks', 'order']

    def validate_marks(self, value):
        """Validate marks are positive."""
        if value < 1:
            raise serializers.ValidationError('Marks must be at least 1')
        return value

    def validate(self, data):
        """Validate test case against question."""
        question = self.context.get('question')
        if not question:
            raise serializers.ValidationError('Question context required')

        # Check if adding this test case would exceed question marks
        new_marks = data.get('marks', 0)
        existing_marks = sum(
            tc.marks for tc in question.test_cases.all()
        )

        if existing_marks + new_marks > question.total_marks:
            raise serializers.ValidationError({
                'marks': f'Adding {new_marks} marks would exceed total marks of {question.total_marks}'
            })

        return data

    def create(self, validated_data):
        """Create test case."""
        question = self.context['question']
        return TestCase.objects.create(question=question, **validated_data)


class TestCaseUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating test cases."""

    class Meta:
        model = TestCase
        fields = ['input', 'expected_output', 'is_sample', 'marks', 'order']

    def validate_marks(self, value):
        """Validate marks are positive."""
        if value < 1:
            raise serializers.ValidationError('Marks must be at least 1')
        return value

    def validate(self, data):
        """Validate test case against question."""
        instance = self.instance
        question = instance.question

        # Check if updating marks would exceed question marks
        if 'marks' in data:
            new_marks = data['marks']
            other_marks = sum(
                tc.marks for tc in question.test_cases.exclude(id=instance.id)
            )

            if other_marks + new_marks > question.total_marks:
                raise serializers.ValidationError({
                    'marks': f'Total marks ({other_marks + new_marks}) would exceed question total ({question.total_marks})'
                })

        return data


class QuestionStatsSerializer(serializers.Serializer):
    """Serializer for question statistics."""

    total_questions = serializers.IntegerField(read_only=True)
    by_difficulty = serializers.DictField(child=serializers.IntegerField(), read_only=True)
    by_status = serializers.DictField(child=serializers.IntegerField(), read_only=True)
    by_topic = serializers.DictField(child=serializers.IntegerField(), read_only=True)
    average_marks = serializers.FloatField(read_only=True)
