"""
API Views for Code Submissions.

Handles submission endpoints for creating and viewing submissions and results.
"""

import logging
from uuid import UUID
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from assessments.models import AssessmentAssignment, AssessmentQuestion
from questions.models import TestCase as QuestionTestCase
from .models import CodeSubmission, TestCaseVerdict, ExecutionLog
from .serializers import (
    CodeSubmissionCreateSerializer, CodeSubmissionStatusSerializer,
    CodeSubmissionResultSerializer, CodeSubmissionListSerializer,
    CodeSubmissionDetailSerializer, ExecutionLogSerializer,
    SubmissionStatsSerializer, ClientEvaluationCreateSerializer,
    ClientEvaluationResultsSerializer,
)
from .permissions import IsStudent, IsOwnSubmission, CanViewSubmissionResult
from .services import SubmissionService, is_stale_evaluation
from .execution_service import ComparisonService, DockerExecutionService
from .tasks import execute_submission
from .client_evaluation import (
    ClientEvaluationError,
    ClientEvaluationService,
    build_case_snapshot,
    public_case_snapshot,
)

logger = logging.getLogger(__name__)


class SubmissionPagination(PageNumberPagination):
    """Pagination for submissions."""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class RunCodeView(APIView):
    """Run student code against visible sample cases without saving a submission."""

    permission_classes = [permissions.IsAuthenticated, IsStudent]

    def post(self, request):
        if not settings.SERVER_DOCKER_EXECUTION_ENABLED:
            return Response(
                {"detail": "Server-side execution is disabled. Use a supported client runner."},
                status=status.HTTP_410_GONE,
            )
        assignment_id = request.data.get("assignment_id")
        if not assignment_id:
            return Response({"assignment_id": "This field is required."}, status=400)

        serializer = CodeSubmissionCreateSerializer(
            data=request.data,
            context={
                "request": request,
                "assignment_id": assignment_id,
                "allow_submission_grace": False,
            },
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        assignment = get_object_or_404(
            AssessmentAssignment, id=assignment_id, student=request.user
        )
        assessment_question = get_object_or_404(
            AssessmentQuestion,
            id=serializer.validated_data["question_id"],
            assessment=assignment.assessment,
        )
        sample_cases = QuestionTestCase.objects.filter(
            question=assessment_question.question, is_sample=True
        ).order_by("order")
        if not sample_cases.exists():
            return Response(
                {"error": "This question does not have a sample test case."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        execution_service = None
        working_dir = None
        try:
            execution_service = DockerExecutionService()
            working_dir = execution_service._create_execution_container()
            compiled, compile_error, compile_time = execution_service.compile_code(
                serializer.validated_data["source_code"], working_dir
            )
            if not compiled:
                return Response({
                    "status": "compilation_error",
                    "verdict": "compilation_error",
                    "compilation_error": compile_error,
                    "compilation_time_ms": int(compile_time),
                    "test_results": [],
                })

            test_results = []
            for case in sample_cases:
                run_result = execution_service.execute_test_case(
                    working_dir,
                    case.input,
                    timeout_seconds=min(
                        10,
                        max(1, assessment_question.question.time_limit_seconds),
                    ),
                )
                actual_output = run_result.get("output", "")
                if run_result["status"] != "accepted":
                    verdict = run_result["status"]
                else:
                    verdict = (
                        "accepted"
                        if ComparisonService.compare_outputs(actual_output, case.expected_output)
                        else "wrong_answer"
                    )
                test_results.append({
                    "order": case.order,
                    "status": verdict,
                    "expected_output": case.expected_output,
                    "actual_output": actual_output,
                    "error": run_result.get("error", ""),
                    "execution_time_ms": int(run_result.get("execution_time_ms", 0)),
                })

            passed = sum(result["status"] == "accepted" for result in test_results)
            return Response({
                "status": "completed",
                "verdict": "accepted" if passed == len(test_results) else "wrong_answer",
                "compilation_time_ms": int(compile_time),
                "passed_test_cases": passed,
                "total_test_cases": len(test_results),
                "test_results": test_results,
            })
        except Exception:
            logger.exception("Dry-run code execution failed")
            return Response(
                {
                    "error": (
                        "Code execution is unavailable because the Docker engine "
                        "could not be reached. Start Docker and retry."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        finally:
            if execution_service and working_dir:
                execution_service.cleanup(working_dir)


class ExecutionCasesView(APIView):
    """Return the cases an assigned student may execute on their own client."""

    permission_classes = [permissions.IsAuthenticated, IsStudent]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "client_execution_cases"

    def get(self, request):
        submission_id = request.query_params.get("submission_id")
        if submission_id:
            try:
                submission_id = UUID(submission_id)
            except (ValueError, TypeError, AttributeError):
                return Response(
                    {"detail": "submission_id must be a valid UUID."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            submission = get_object_or_404(
                CodeSubmission.objects.exclude(
                    runner_type=CodeSubmission.RunnerType.SERVER_DOCKER,
                ),
                id=submission_id,
                student=request.user,
                status=CodeSubmission.Status.PENDING,
                client_test_cases_snapshot__isnull=False,
            )
            return Response(
                public_case_snapshot(
                    submission.assignment_id,
                    submission.client_test_cases_snapshot,
                ),
                status=status.HTTP_200_OK,
            )

        assignment_id = request.query_params.get("assignment_id")
        question_id = request.query_params.get("question_id")
        if not assignment_id or not question_id:
            missing_fields = {}
            if not assignment_id:
                missing_fields["assignment_id"] = "This field is required."
            if not question_id:
                missing_fields["question_id"] = "This field is required."
            return Response(
                {
                    "detail": "Assignment and question IDs are required.",
                    "fields": missing_fields,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            assignment_id = UUID(assignment_id)
            question_id = UUID(question_id)
        except (ValueError, TypeError, AttributeError):
            return Response(
                {"detail": "assignment_id and question_id must be valid UUIDs."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assignment = get_object_or_404(
            AssessmentAssignment,
            id=assignment_id,
            student=request.user,
        )
        is_eligible, error = SubmissionService.validate_submission_eligibility(
            student_id=str(request.user.id),
            assignment_id=str(assignment.id),
            question_id=str(question_id),
        )
        if not is_eligible:
            return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)

        assessment_question = get_object_or_404(
            AssessmentQuestion,
            id=question_id,
            assessment_id=assignment.assessment_id,
        )
        try:
            snapshot = build_case_snapshot(assessment_question)
        except ClientEvaluationError as error:
            return Response(
                {"detail": error.detail},
                status=error.status_code,
            )
        return Response(
            public_case_snapshot(assignment.id, snapshot),
            status=status.HTTP_200_OK,
        )


class ClientEvaluationCreateView(APIView):
    """Save a client-side submission before the client compiles and runs it."""

    permission_classes = [permissions.IsAuthenticated, IsStudent]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "client_evaluation_create"

    def post(self, request):
        serializer = ClientEvaluationCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        ip_address = (
            forwarded_for.split(",")[0].strip()
            if forwarded_for
            else request.META.get("REMOTE_ADDR")
        )
        try:
            submission, created = ClientEvaluationService.create_pending_submission(
                student=request.user,
                payload=serializer.validated_data,
                ip_address=ip_address,
            )
        except ClientEvaluationError as error:
            return Response({"detail": error.detail}, status=error.status_code)
        except Exception:
            logger.exception("Could not create client evaluation for %s", request.user.id)
            return Response(
                {"detail": "The submission could not be saved. Please retry."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        response_data = {
            "submission_id": str(submission.id),
            "status": submission.status,
        }
        response_data.update(public_case_snapshot(
            submission.assignment_id,
            submission.client_test_cases_snapshot,
        ))
        if submission.status == CodeSubmission.Status.COMPLETED:
            response_data["result"] = CodeSubmissionResultSerializer(submission).data
        return Response(
            response_data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class ClientEvaluationResultsView(APIView):
    """Compare client-reported outputs and complete a pending submission."""

    permission_classes = [permissions.IsAuthenticated, IsStudent]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "client_evaluation_results"

    def post(self, request, submission_id):
        serializer = ClientEvaluationResultsSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            submission, _ = ClientEvaluationService.complete_submission(
                submission_id=submission_id,
                student=request.user,
                payload=serializer.validated_data,
            )
        except ClientEvaluationError as error:
            return Response({"detail": error.detail}, status=error.status_code)
        except Exception:
            logger.exception("Could not complete client evaluation %s", submission_id)
            return Response(
                {"detail": "The results could not be saved. Please retry."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if submission.assignment.status == AssessmentAssignment.Status.SUBMITTED:
            try:
                SubmissionService.evaluate_assignment_submissions(submission.assignment)
            except Exception:
                logger.exception(
                    "Client result saved but assignment score refresh failed for %s",
                    submission.assignment_id,
                )
                return Response(
                    {
                        "detail": (
                            "The evaluation result was saved, but the assessment score "
                            "could not be refreshed. Retry this request."
                        ),
                        "submission_id": str(submission.id),
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

        return Response(
            CodeSubmissionResultSerializer(submission).data,
            status=status.HTTP_200_OK,
        )


class CodeSubmissionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing code submissions."""

    serializer_class = CodeSubmissionListSerializer
    permission_classes = [permissions.IsAuthenticated, IsStudent]
    pagination_class = SubmissionPagination

    def get_queryset(self):
        """Get submissions for current student."""
        user = self.request.user

        if user.role == 'student':
            return CodeSubmission.objects.filter(student=user).order_by('-created_at')

        return CodeSubmission.objects.none()

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'retrieve':
            return CodeSubmissionDetailSerializer
        return CodeSubmissionListSerializer

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Get current status of a submission."""
        submission = self.get_object()

        # Check permission
        if submission.student != request.user:
            return Response(
                {'error': 'Cannot view other students\' submissions'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = CodeSubmissionStatusSerializer(submission)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def result(self, request, pk=None):
        """Get detailed result of a submission."""
        submission = self.get_object()

        # Check permission
        if submission.student != request.user:
            return Response(
                {'error': 'Cannot view other students\' submissions'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Only show results if submission is completed
        if submission.status != CodeSubmission.Status.COMPLETED:
            return Response(
                {'error': 'Submission not yet completed'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = CodeSubmissionResultSerializer(submission)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def execution_log(self, request, pk=None):
        """Get execution log for a submission."""
        submission = self.get_object()

        # Check permission
        if submission.student != request.user:
            return Response(
                {'error': 'Cannot view other students\' submissions'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            log = ExecutionLog.objects.get(submission=submission)
            serializer = ExecutionLogSerializer(log)
            return Response(serializer.data)
        except ExecutionLog.DoesNotExist:
            return Response(
                {'error': 'Execution log not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class SubmissionCreateView(viewsets.ViewSet):
    """ViewSet for creating code submissions."""

    permission_classes = [permissions.IsAuthenticated, IsStudent]

    def create(self, request):
        """Create one final code submission from the root create endpoint."""
        return self._create_submission(request, request.data.get("assignment_id"))

    @action(detail=False, methods=['post'], url_path='submit/(?P<assignment_id>[0-9a-f-]+)')
    def submit_code(self, request, assignment_id=None):
        """
        Submit code for an assignment question.

        POST /api/submissions/submit/{assignment_id}/
        {
            "question_id": "uuid",
            "source_code": "..."
        }
        """
        return self._create_submission(request, assignment_id)

    def _create_submission(self, request, assignment_id):
        if not settings.SERVER_DOCKER_EXECUTION_ENABLED:
            return Response(
                {"detail": "Server-side execution is disabled. Use a supported client runner."},
                status=status.HTTP_410_GONE,
            )
        if not assignment_id:
            return Response(
                {'error': 'Assignment ID required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = CodeSubmissionCreateSerializer(
            data=request.data,
            context={
                'request': request,
                'assignment_id': assignment_id,
                'allow_submission_grace': True,
            }
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Create submission
            submission, error = SubmissionService.create_submission(
                student_id=str(request.user.id),
                assignment_id=assignment_id,
                question_id=str(serializer.validated_data['question_id']),
                source_code=serializer.validated_data['source_code'],
                ip_address=serializer.validated_data['ip_address'],
                allow_submission_grace=True,
            )

            if error:
                return Response(
                    {'error': error},
                    status=status.HTTP_400_BAD_REQUEST
                )

            logger.info(
                f"Created submission {submission.id} for student {request.user.id}, "
                f"assignment {assignment_id}"
            )

            # Trigger async execution. Do not leave a pending submission behind
            # if the broker is down and the task cannot be queued.
            try:
                execute_submission.delay(
                    str(submission.id),
                    submission.evaluation_generation,
                )
            except Exception:
                logger.exception("Could not queue execution for submission %s", submission.id)
                submission.status = CodeSubmission.Status.FAILED
                submission.verdict = CodeSubmission.Verdict.INTERNAL_ERROR
                submission.compilation_error = (
                    "Evaluation could not start because the background queue is unavailable."
                )
                submission.execution_completed_at = timezone.now()
                submission.save(update_fields=[
                    "status",
                    "verdict",
                    "compilation_error",
                    "execution_completed_at",
                    "updated_at",
                ])
                return Response(
                    {
                        "error": (
                            "The submission could not be queued for evaluation. "
                            "Make sure Redis and the Celery worker are running, then try again."
                        ),
                        "submission_id": str(submission.id),
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

            logger.info(f"Queued execution for submission {submission.id}")

            return Response(
                {
                    'message': 'Submission received and queued for execution',
                    'submission_id': str(submission.id),
                    'status': submission.status
                },
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            logger.exception(f"Error creating submission: {e}")
            return Response(
                {'error': f'Error creating submission: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SubmissionStatusView(viewsets.ViewSet):
    """ViewSet for checking submission status."""

    permission_classes = [permissions.IsAuthenticated]

    def retrieve(self, request, pk=None):
        """Return submission status at /api/submissions/status/{id}/."""
        try:
            submission = CodeSubmission.objects.get(id=pk)
        except CodeSubmission.DoesNotExist:
            return Response({"error": "Submission not found"}, status=404)

        if request.user.role == "student" and submission.student_id != request.user.id:
            return Response(
                {"error": "Cannot view another student's submission"},
                status=status.HTTP_403_FORBIDDEN,
            )
        if request.user.role == "faculty" and submission.assignment.assessment.created_by_id != request.user.id:
            return Response(
                {"error": "Cannot view submissions for another faculty member's assessment"},
                status=status.HTTP_403_FORBIDDEN,
            )
        if request.user.role not in {"student", "faculty"}:
            return Response({"error": "Insufficient permissions"}, status=403)

        return Response(CodeSubmissionStatusSerializer(submission).data)

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Restart a failed or stale evaluation for its owning faculty member."""
        if request.user.role != "faculty" or not request.user.is_faculty_approved:
            return Response(
                {"error": "Only approved faculty can retry evaluations."},
                status=status.HTTP_403_FORBIDDEN,
            )

        generation = None
        try:
            with transaction.atomic():
                submission = CodeSubmission.objects.select_for_update().select_related(
                    "assignment__assessment"
                ).get(id=pk)
                if submission.assignment.assessment.created_by_id != request.user.id:
                    return Response(
                        {"error": "You can only retry evaluations for your assessments."},
                        status=status.HTTP_403_FORBIDDEN,
                    )
                if not settings.SERVER_DOCKER_EXECUTION_ENABLED:
                    return Response(
                        {"error": "Server-side code execution is disabled."},
                        status=status.HTTP_410_GONE,
                    )
                if submission.runner_type != CodeSubmission.RunnerType.SERVER_DOCKER:
                    return Response(
                        {
                            "error": (
                                "Client-side evaluations cannot be rerun by the server. "
                                "The student must resubmit the code from a supported client."
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if submission.status != CodeSubmission.Status.FAILED and not is_stale_evaluation(submission):
                    return Response(
                        {"error": "Only failed or stale evaluations can be retried."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                submission.evaluation_generation += 1
                submission.status = CodeSubmission.Status.PENDING
                submission.verdict = CodeSubmission.Verdict.NOT_EVALUATED
                submission.marks_obtained = None
                submission.compilation_error = None
                submission.compilation_time_ms = None
                submission.total_test_cases = 0
                submission.passed_test_cases = 0
                submission.failed_test_cases = 0
                submission.execution_time_ms = None
                submission.max_memory_used_mb = None
                submission.execution_job_id = None
                submission.execution_started_at = None
                submission.execution_completed_at = None
                submission.save(update_fields=[
                    "evaluation_generation",
                    "status",
                    "verdict",
                    "marks_obtained",
                    "compilation_error",
                    "compilation_time_ms",
                    "total_test_cases",
                    "passed_test_cases",
                    "failed_test_cases",
                    "execution_time_ms",
                    "max_memory_used_mb",
                    "execution_job_id",
                    "execution_started_at",
                    "execution_completed_at",
                    "updated_at",
                ])
                TestCaseVerdict.objects.filter(submission=submission).delete()
                ExecutionLog.objects.filter(submission=submission).delete()
                generation = submission.evaluation_generation

            execute_submission.delay(str(submission.id), generation)
        except CodeSubmission.DoesNotExist:
            return Response({"error": "Submission not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception:
            logger.exception("Could not queue retry for submission %s", pk)
            if generation is not None:
                try:
                    CodeSubmission.objects.filter(
                        id=pk,
                        evaluation_generation=generation,
                    ).update(
                        status=CodeSubmission.Status.FAILED,
                        verdict=CodeSubmission.Verdict.INTERNAL_ERROR,
                        compilation_error="Evaluation could not be queued. Check the background worker and retry.",
                        execution_completed_at=timezone.now(),
                        updated_at=timezone.now(),
                    )
                except Exception:
                    logger.exception("Could not mark failed retry for submission %s", pk)
            return Response(
                {"error": "Evaluation could not be queued. Check the background worker and retry."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response({
            "message": "Evaluation retry queued.",
            "submission_id": str(submission.id),
            "status": CodeSubmission.Status.PENDING,
            "evaluation_generation": generation,
        }, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=['get'], url_path='status/(?P<submission_id>[0-9a-f-]+)')
    def get_status(self, request, submission_id=None):
        """
        Get current status of a submission.

        GET /api/submissions/status/{submission_id}/
        """
        if not submission_id:
            return Response(
                {'error': 'Submission ID required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            submission = CodeSubmission.objects.get(id=submission_id)

            # Check permission
            if submission.student != request.user and request.user.role != 'faculty':
                return Response(
                    {'error': 'Cannot view other students\' submissions'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Faculty can view assignments they created
            if request.user.role == 'faculty':
                if submission.assignment.assessment.created_by != request.user:
                    return Response(
                        {'error': 'Cannot view submissions for other faculty\'s assessments'},
                        status=status.HTTP_403_FORBIDDEN
                    )

            status_data = SubmissionService.get_submission_status(submission_id)
            return Response(status_data)

        except CodeSubmission.DoesNotExist:
            return Response(
                {'error': 'Submission not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'], url_path='result/(?P<submission_id>[0-9a-f-]+)')
    def get_result(self, request, submission_id=None):
        """
        Get detailed result of a submission.

        GET /api/submissions/result/{submission_id}/
        """
        if not submission_id:
            return Response(
                {'error': 'Submission ID required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            submission = CodeSubmission.objects.get(id=submission_id)

            # Check permission
            if submission.student != request.user:
                return Response(
                    {'error': 'Cannot view other students\' submissions'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Only show results if submission is completed
            if submission.status != CodeSubmission.Status.COMPLETED:
                return Response(
                    {'error': 'Submission not yet completed'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            result_data = SubmissionService.get_submission_result(
                submission_id,
                show_hidden=False  # Never show hidden test details to students
            )

            return Response(result_data)

        except CodeSubmission.DoesNotExist:
            return Response(
                {'error': 'Submission not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class SubmissionListView(viewsets.ViewSet):
    """ViewSet for listing submissions."""

    permission_classes = [permissions.IsAuthenticated]
    pagination_class = SubmissionPagination

    @action(detail=False, methods=['get'], url_path='list')
    def list_submissions(self, request):
        """
        List all submissions for current student.

        GET /api/submissions/list/
        """
        if request.user.role != 'student':
            return Response(
                {'error': 'Only students can list submissions'},
                status=status.HTTP_403_FORBIDDEN
            )

        submissions = CodeSubmission.objects.filter(
            student=request.user
        ).order_by('-created_at')

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(submissions, request)

        if page is not None:
            serializer = CodeSubmissionListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = CodeSubmissionListSerializer(submissions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='by_assignment/(?P<assignment_id>[0-9a-f-]+)')
    def list_by_assignment(self, request, assignment_id=None):
        """
        List submissions for a specific assignment.

        GET /api/submissions/by_assignment/{assignment_id}/
        """
        if not assignment_id:
            return Response(
                {'error': 'Assignment ID required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from assessments.models import AssessmentAssignment

        try:
            assignment = AssessmentAssignment.objects.get(id=assignment_id)

            if request.user.role == 'student':
                if assignment.student != request.user:
                    return Response(
                        {'error': 'Cannot view other students\' submissions'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            elif request.user.role == 'faculty':
                if assignment.assessment.created_by != request.user:
                    return Response(
                        {'error': 'Cannot view submissions for other faculty\'s assessments'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            else:
                return Response(
                    {'error': 'Insufficient permissions'},
                    status=status.HTTP_403_FORBIDDEN
                )

            submissions = CodeSubmission.objects.filter(
                assignment=assignment
            ).order_by('-created_at')

            paginator = self.pagination_class()
            page = paginator.paginate_queryset(submissions, request)

            if page is not None:
                serializer = CodeSubmissionListSerializer(page, many=True)
                return paginator.get_paginated_response(serializer.data)

            serializer = CodeSubmissionListSerializer(submissions, many=True)
            return Response(serializer.data)

        except AssessmentAssignment.DoesNotExist:
            return Response(
                {'error': 'Assignment not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'], url_path='stats')
    def submission_stats(self, request):
        """
        Get submission statistics for current student.

        GET /api/submissions/stats/
        """
        if request.user.role != 'student':
            return Response(
                {'error': 'Only students can view stats'},
                status=status.HTTP_403_FORBIDDEN
            )

        from django.db.models import Count, Avg

        submissions = CodeSubmission.objects.filter(student=request.user)

        stats = {
            'total_submissions': submissions.count(),
            'pending_submissions': submissions.filter(
                status=CodeSubmission.Status.PENDING
            ).count(),
            'completed_submissions': submissions.filter(
                status=CodeSubmission.Status.COMPLETED
            ).count(),
            'accepted_submissions': submissions.filter(
                verdict=CodeSubmission.Verdict.ACCEPTED
            ).count(),
            'average_marks': submissions.filter(
                marks_obtained__isnull=False
            ).aggregate(avg=Avg('marks_obtained'))['avg'] or 0,
            'success_rate': (
                submissions.filter(verdict=CodeSubmission.Verdict.ACCEPTED).count() /
                submissions.count() * 100 if submissions.count() > 0 else 0
            ),
            'compilation_errors': submissions.filter(
                verdict=CodeSubmission.Verdict.COMPILATION_ERROR
            ).count(),
            'runtime_errors': submissions.filter(
                verdict=CodeSubmission.Verdict.RUNTIME_ERROR
            ).count(),
        }

        serializer = SubmissionStatsSerializer(stats)
        return Response(serializer.data)
