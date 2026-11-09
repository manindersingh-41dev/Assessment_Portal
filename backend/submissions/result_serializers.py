"""
Serializers for Submission Management and Results.

Handles display and transformation of submission and result data.
"""

from rest_framework import serializers
from django.utils import timezone

from submissions.models import CodeSubmission, TestCaseVerdict
from assessments.models import AssessmentResult, AssessmentAssignment
from .evaluation_service import ResultCalculationService, AssessmentEvaluationService


class QuestionResultSerializer(serializers.Serializer):
    """Serializer for question-wise results."""

    question_id = serializers.UUIDField()
    question_title = serializers.CharField()
    question_order = serializers.IntegerField()
    marks_obtained = serializers.IntegerField()
    total_marks = serializers.IntegerField()
    verdict = serializers.CharField()
    percentage = serializers.FloatField()


class AssignmentResultSerializer(serializers.Serializer):
    """Serializer for complete assignment results."""

    assignment_id = serializers.UUIDField()
    student_id = serializers.UUIDField()
    student_name = serializers.CharField()
    student_email = serializers.CharField()
    assessment_id = serializers.UUIDField()
    assessment_title = serializers.CharField()
    total_marks_obtained = serializers.IntegerField()
    total_marks = serializers.IntegerField()
    percentage = serializers.FloatField()
    passed = serializers.BooleanField()
    attempted_questions = serializers.IntegerField()
    total_questions = serializers.IntegerField()
    question_results = QuestionResultSerializer(many=True)
    evaluated_at = serializers.DateTimeField()


class SubmissionSummarySerializer(serializers.ModelSerializer):
    """Serializer for submission summary."""

    assessment_title = serializers.CharField(source='assignment.assessment.title', read_only=True)
    question_title = serializers.CharField(source='question.question.title', read_only=True)
    question_order = serializers.IntegerField(source='question.order', read_only=True)
    verdict_display = serializers.CharField(source='get_verdict_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = CodeSubmission
        fields = [
            'id', 'assessment_title', 'question_title', 'question_order', 'status', 'status_display',
            'verdict', 'verdict_display', 'marks_obtained', 'total_test_cases',
            'passed_test_cases', 'attempt_number', 'created_at'
        ]
        read_only_fields = fields


class StudentSubmissionHistorySerializer(serializers.Serializer):
    """Serializer for student submission history."""

    submission_id = serializers.UUIDField(source='id')
    assessment_title = serializers.CharField()
    question_title = serializers.CharField()
    question_order = serializers.IntegerField()
    status = serializers.CharField()
    status_display = serializers.CharField()
    verdict = serializers.CharField()
    verdict_display = serializers.CharField()
    marks_obtained = serializers.IntegerField(allow_null=True)
    total_test_cases = serializers.IntegerField()
    passed_test_cases = serializers.IntegerField()
    attempt_number = serializers.IntegerField()
    created_at = serializers.DateTimeField()


class AssessmentSubmissionOverviewSerializer(serializers.Serializer):
    """Serializer for assessment submission overview."""

    submission_id = serializers.UUIDField(source='id')
    assessment_id = serializers.UUIDField()
    assessment_title = serializers.CharField()
    student_name = serializers.CharField()
    student_email = serializers.CharField()
    question_title = serializers.CharField()
    question_order = serializers.IntegerField()
    status = serializers.CharField()
    status_display = serializers.CharField()
    verdict = serializers.CharField()
    verdict_display = serializers.CharField()
    marks_obtained = serializers.IntegerField(allow_null=True)
    total_test_cases = serializers.IntegerField()
    passed_test_cases = serializers.IntegerField()
    attempt_number = serializers.IntegerField()
    created_at = serializers.DateTimeField()


class QuestionStatisticsSerializer(serializers.Serializer):
    """Serializer for question statistics."""

    total_submissions = serializers.IntegerField()
    accepted = serializers.IntegerField()
    wrong_answer = serializers.IntegerField()
    compilation_error = serializers.IntegerField()
    runtime_error = serializers.IntegerField()
    average_marks = serializers.FloatField()
    acceptance_rate = serializers.FloatField()


class AssessmentStatisticsSerializer(serializers.Serializer):
    """Serializer for assessment statistics."""

    assessment_id = serializers.UUIDField()
    assessment_title = serializers.CharField()
    total_students = serializers.IntegerField()
    evaluated = serializers.IntegerField()
    pending = serializers.IntegerField()
    passed = serializers.IntegerField()
    failed = serializers.IntegerField()
    pass_rate = serializers.FloatField()
    average_percentage = serializers.FloatField()
    average_marks = serializers.FloatField()


class StudentWiseResultSerializer(serializers.ModelSerializer):
    """Serializer for student-wise results."""

    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    student_email = serializers.CharField(source='student.email', read_only=True)
    assessment_title = serializers.CharField(source='assessment.title', read_only=True)
    passing_marks = serializers.IntegerField(source='assessment.passing_marks', read_only=True)

    class Meta:
        model = AssessmentResult
        fields = [
            'id', 'student_name', 'student_email', 'assessment_title',
            'total_marks_obtained', 'passing_marks', 'percentage', 'passed',
            'attempted_at', 'evaluated_at', 'feedback'
        ]
        read_only_fields = fields


class AssessmentResultExportSerializer(serializers.Serializer):
    """Serializer for exporting assessment results."""

    student_name = serializers.CharField()
    student_email = serializers.CharField()
    total_marks = serializers.IntegerField()
    passing_marks = serializers.IntegerField()
    percentage = serializers.FloatField()
    status = serializers.CharField()


class SubmissionSourceCodeSerializer(serializers.ModelSerializer):
    """Serializer for viewing submission source code."""

    question_title = serializers.CharField(source='question.question.title', read_only=True)
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    verdict_display = serializers.CharField(source='get_verdict_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = CodeSubmission
        fields = [
            'id', 'question_title', 'student_name', 'source_code',
            'status', 'status_display', 'verdict', 'verdict_display',
            'marks_obtained', 'compilation_error', 'created_at'
        ]
        read_only_fields = fields


class SubmissionTestCaseDetailsSerializer(serializers.Serializer):
    """Serializer for detailed test case results."""

    test_case_order = serializers.IntegerField()
    is_sample = serializers.BooleanField()
    status = serializers.CharField()
    marks_obtained = serializers.IntegerField()
    execution_time_ms = serializers.IntegerField()
    memory_used_mb = serializers.FloatField()
    actual_output = serializers.CharField(required=False, allow_blank=True)
    error_message = serializers.CharField(required=False, allow_blank=True)
