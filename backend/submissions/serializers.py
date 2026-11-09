"""
Serializers for Code Submissions.

Handles validation and transformation for submission data.
"""

from rest_framework import serializers
from django.utils import timezone

from .models import CodeSubmission, TestCaseVerdict, ExecutionLog
from .services import (
    SubmissionService,
    SubmissionSecurityService,
    is_stale_evaluation,
)


class TestCaseVerdictSerializer(serializers.ModelSerializer):
    """Serializer for test case verdict results."""

    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = TestCaseVerdict
        fields = [
            'id', 'test_case_order', 'is_sample', 'status', 'status_display',
            'marks_obtained', 'execution_time_ms', 'memory_used_mb',
            'expected_output', 'actual_output', 'error_message'
        ]
        read_only_fields = ['id', 'status_display']


class TestCaseVerdictHiddenSerializer(serializers.ModelSerializer):
    """Expose only a pass/fail result for hidden test cases."""

    status = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()

    def get_status(self, obj):
        return 'accepted' if obj.status == TestCaseVerdict.Status.ACCEPTED else 'failed'

    def get_status_display(self, obj):
        return 'Passed' if obj.status == TestCaseVerdict.Status.ACCEPTED else 'Failed'

    class Meta:
        model = TestCaseVerdict
        fields = [
            'test_case_order', 'is_sample', 'status', 'status_display',
        ]


def serialize_student_test_case_verdicts(submission):
    """Serialize visible output details and hidden pass/fail only."""
    verdicts = submission.test_case_verdicts.all().order_by('test_case_order')
    results = []
    for verdict in verdicts:
        serializer_class = (
            TestCaseVerdictSerializer
            if verdict.is_sample
            else TestCaseVerdictHiddenSerializer
        )
        results.append(serializer_class(verdict).data)
    return results


class CodeSubmissionStatusSerializer(serializers.ModelSerializer):
    """Serializer for submission status."""

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    verdict_display = serializers.CharField(source='get_verdict_display', read_only=True)
    success_rate = serializers.SerializerMethodField()
    error_message = serializers.SerializerMethodField()
    test_case_verdicts = serializers.SerializerMethodField()
    is_stale = serializers.SerializerMethodField()
    can_resume_client_evaluation = serializers.SerializerMethodField()

    class Meta:
        model = CodeSubmission
        fields = [
            'id', 'runner_type', 'runner_version', 'compiler_version',
            'status', 'status_display', 'verdict', 'verdict_display',
            'marks_obtained', 'total_test_cases', 'passed_test_cases',
            'failed_test_cases', 'success_rate',
            'compilation_error', 'error_message',
            'compilation_time_ms', 'execution_time_ms', 'max_memory_used_mb',
            'test_case_verdicts',
            'execution_started_at', 'execution_completed_at',
            'evaluation_generation', 'updated_at', 'is_stale',
            'can_resume_client_evaluation',
        ]
        read_only_fields = fields

    def get_success_rate(self, obj):
        """Calculate success rate percentage."""
        return obj.get_success_rate()

    def get_test_case_verdicts(self, obj):
        return serialize_student_test_case_verdicts(obj)

    def get_is_stale(self, obj):
        return is_stale_evaluation(obj)

    def get_can_resume_client_evaluation(self, obj):
        return (
            obj.runner_type != CodeSubmission.RunnerType.SERVER_DOCKER
            and obj.status == CodeSubmission.Status.PENDING
        )

    def get_error_message(self, obj):
        """Return a student-safe runtime error from a visible sample test case."""
        if obj.compilation_error:
            return obj.compilation_error
        return obj.test_case_verdicts.filter(
            is_sample=True
        ).exclude(
            error_message__isnull=True
        ).exclude(
            error_message=''
        ).values_list('error_message', flat=True).first()


class CodeSubmissionResultSerializer(serializers.ModelSerializer):
    """Serializer for submission result with test case verdicts."""

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    verdict_display = serializers.CharField(source='get_verdict_display', read_only=True)
    success_rate = serializers.SerializerMethodField()
    test_case_verdicts = serializers.SerializerMethodField()

    class Meta:
        model = CodeSubmission
        fields = [
            'id', 'runner_type', 'runner_version', 'compiler_version',
            'status', 'status_display', 'verdict', 'verdict_display',
            'marks_obtained', 'total_test_cases', 'passed_test_cases',
            'failed_test_cases', 'success_rate',
            'compilation_error', 'compilation_time_ms',
            'execution_time_ms', 'max_memory_used_mb',
            'test_case_verdicts',
            'execution_started_at', 'execution_completed_at'
        ]
        read_only_fields = fields

    def get_success_rate(self, obj):
        """Calculate success rate percentage."""
        return obj.get_success_rate()

    def get_test_case_verdicts(self, obj):
        """Return visible outputs and hidden pass/fail only."""
        return serialize_student_test_case_verdicts(obj)


class CodeSubmissionCreateSerializer(serializers.Serializer):
    """Serializer for creating a code submission."""

    assignment_id = serializers.UUIDField(required=False, write_only=True)
    question_id = serializers.UUIDField(required=True)
    source_code = serializers.CharField(required=True)

    def validate_source_code(self, value):
        """Validate source code."""
        is_valid, error = SubmissionSecurityService.validate_source_code(value)

        if not is_valid:
            raise serializers.ValidationError(error)

        return value

    def validate(self, data):
        """Validate submission eligibility."""
        request = self.context.get('request')
        assignment_id = data.get('assignment_id') or self.context.get('assignment_id')

        if not request or not request.user:
            raise serializers.ValidationError('Authentication required')

        if not assignment_id:
            raise serializers.ValidationError('Assignment ID required')
        assignment_id = str(assignment_id)

        # Check eligibility
        is_eligible, error = SubmissionService.validate_submission_eligibility(
            student_id=str(request.user.id),
            assignment_id=assignment_id,
            question_id=str(data['question_id']),
            allow_submission_grace=self.context.get('allow_submission_grace', False),
        )

        if not is_eligible:
            raise serializers.ValidationError(error)

        data['assignment_id'] = assignment_id
        data['student_id'] = str(request.user.id)
        data['ip_address'] = self._get_client_ip(request)

        return data

    @staticmethod
    def _get_client_ip(request):
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class ClientEvaluationCreateSerializer(serializers.Serializer):
    """Validate the request that records a client-side evaluation attempt."""

    client_submission_id = serializers.UUIDField()
    assignment_id = serializers.UUIDField()
    question_id = serializers.UUIDField()
    source_code = serializers.CharField(
        max_length=100_000,
        allow_blank=False,
        trim_whitespace=False,
    )
    runner_type = serializers.ChoiceField(
        choices=[
            CodeSubmission.RunnerType.WEB_WASM,
            CodeSubmission.RunnerType.DESKTOP_GCC,
        ]
    )
    runner_version = serializers.CharField(max_length=100, allow_blank=False)
    compiler_version = serializers.CharField(
        max_length=255,
        allow_blank=True,
        required=False,
        default="",
    )

    def validate_source_code(self, value):
        if not value.strip():
            raise serializers.ValidationError("Source code cannot be empty.")
        if "\x00" in value:
            raise serializers.ValidationError("Source code cannot contain a null character.")
        if len(value.encode("utf-8")) > 100_000:
            raise serializers.ValidationError("Source code cannot exceed 100 KB.")
        return value


class ClientTestResultSerializer(serializers.Serializer):
    """One reported result from either supported local runner."""

    class ExecutionStatus:
        COMPLETED = "completed"
        RUNTIME_ERROR = "runtime_error"
        TIME_LIMIT_EXCEEDED = "time_limit_exceeded"
        MEMORY_LIMIT_EXCEEDED = "memory_limit_exceeded"

        choices = [
            COMPLETED,
            RUNTIME_ERROR,
            TIME_LIMIT_EXCEEDED,
            MEMORY_LIMIT_EXCEEDED,
        ]

    test_case_id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=ExecutionStatus.choices)
    exit_code = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=-255,
        max_value=255,
    )
    duration_ms = serializers.IntegerField(min_value=0, max_value=3_600_000)
    stdout = serializers.CharField(
        max_length=65_536,
        allow_blank=True,
        trim_whitespace=False,
    )
    stderr = serializers.CharField(
        max_length=65_536,
        allow_blank=True,
        trim_whitespace=False,
    )

    def validate_stdout(self, value):
        self._validate_output_text(value, "stdout")
        return value

    def validate_stderr(self, value):
        self._validate_output_text(value, "stderr")
        return value

    @staticmethod
    def _validate_output_text(value, field_name):
        if "\x00" in value:
            raise serializers.ValidationError(f"{field_name} cannot contain a null character.")
        if len(value.encode("utf-8")) > 65_536:
            raise serializers.ValidationError(f"{field_name} cannot exceed 64 KB.")

    def validate(self, attrs):
        if attrs["status"] == self.ExecutionStatus.COMPLETED and attrs.get("exit_code") is None:
            raise serializers.ValidationError(
                {"exit_code": "A completed run must report its exit code."}
            )
        return attrs


class ClientCompilationResultSerializer(serializers.Serializer):
    """Client-reported compilation outcome."""

    status = serializers.ChoiceField(choices=["success", "error"])
    duration_ms = serializers.IntegerField(min_value=0, max_value=3_600_000)
    diagnostics = serializers.CharField(
        max_length=20_000,
        allow_blank=True,
        trim_whitespace=False,
    )

    def validate_diagnostics(self, value):
        if "\x00" in value:
            raise serializers.ValidationError("Compiler diagnostics cannot contain a null character.")
        if len(value.encode("utf-8")) > 20_000:
            raise serializers.ValidationError("Compiler diagnostics cannot exceed 20 KB.")
        return value


class ClientEvaluationResultsSerializer(serializers.Serializer):
    """Validate the results posted for a pending client-side submission."""

    compilation = ClientCompilationResultSerializer()
    test_results = serializers.ListField(
        child=ClientTestResultSerializer(),
        allow_empty=True,
        max_length=250,
    )

    def validate(self, attrs):
        compilation_status = attrs["compilation"]["status"]
        test_results = attrs["test_results"]

        if compilation_status == "error" and test_results:
            raise serializers.ValidationError({
                "test_results": "Test results must be empty when compilation fails."
            })

        case_ids = [result["test_case_id"] for result in test_results]
        if len(case_ids) != len(set(case_ids)):
            raise serializers.ValidationError({
                "test_results": "A test case may only appear once."
            })

        total_output_chars = sum(
            len(result["stdout"].encode("utf-8"))
            + len(result["stderr"].encode("utf-8"))
            for result in test_results
        )
        if total_output_chars > 1_000_000:
            raise serializers.ValidationError({
                "test_results": "Combined test output exceeds the 1 MB limit."
            })

        return attrs


class CodeSubmissionListSerializer(serializers.ModelSerializer):
    """Serializer for listing submissions."""

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    verdict_display = serializers.CharField(source='get_verdict_display', read_only=True)
    question_title = serializers.CharField(source='question.question.title', read_only=True)
    question_id = serializers.UUIDField(source='question.id', read_only=True)
    error_message = serializers.SerializerMethodField()

    class Meta:
        model = CodeSubmission
        fields = [
            'id', 'question_id', 'question_title',
            'runner_type', 'runner_version', 'compiler_version',
            'status', 'status_display',
            'verdict', 'verdict_display', 'marks_obtained',
            'passed_test_cases', 'total_test_cases',
            'attempt_number', 'source_code', 'compilation_error', 'error_message', 'created_at'
        ]
        read_only_fields = fields

    def get_error_message(self, obj):
        """Return a student-safe error from compilation or a visible sample case."""
        if obj.compilation_error:
            return obj.compilation_error
        return obj.test_case_verdicts.filter(
            is_sample=True
        ).exclude(
            error_message__isnull=True
        ).exclude(
            error_message=''
        ).values_list('error_message', flat=True).first()


class CodeSubmissionDetailSerializer(serializers.ModelSerializer):
    """Serializer for submission details."""

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    verdict_display = serializers.CharField(source='get_verdict_display', read_only=True)
    question_title = serializers.CharField(source='question.question.title', read_only=True)
    question_id = serializers.UUIDField(source='question.id', read_only=True)
    success_rate = serializers.SerializerMethodField()
    code_stats = serializers.SerializerMethodField()

    class Meta:
        model = CodeSubmission
        fields = [
            'id', 'question_id', 'question_title',
            'runner_type', 'runner_version', 'compiler_version',
            'status', 'status_display',
            'verdict', 'verdict_display', 'marks_obtained',
            'passed_test_cases', 'total_test_cases', 'success_rate',
            'compilation_error', 'compilation_time_ms',
            'execution_time_ms', 'max_memory_used_mb',
            'code_stats', 'attempt_number',
            'execution_started_at', 'execution_completed_at',
            'created_at'
        ]
        read_only_fields = fields

    def get_success_rate(self, obj):
        """Calculate success rate."""
        return obj.get_success_rate()

    def get_code_stats(self, obj):
        """Get code statistics."""
        return SubmissionSecurityService.get_code_statistics(obj.source_code)


class ExecutionLogSerializer(serializers.ModelSerializer):
    """Serializer for execution logs."""

    class Meta:
        model = ExecutionLog
        fields = [
            'id', 'compilation_output', 'compilation_stderr',
            'execution_output', 'system_info', 'created_at'
        ]
        read_only_fields = fields


class SubmissionStatsSerializer(serializers.Serializer):
    """Serializer for submission statistics."""

    total_submissions = serializers.IntegerField(read_only=True)
    pending_submissions = serializers.IntegerField(read_only=True)
    completed_submissions = serializers.IntegerField(read_only=True)
    accepted_submissions = serializers.IntegerField(read_only=True)
    average_marks = serializers.FloatField(read_only=True)
    success_rate = serializers.FloatField(read_only=True)
    compilation_errors = serializers.IntegerField(read_only=True)
    runtime_errors = serializers.IntegerField(read_only=True)
