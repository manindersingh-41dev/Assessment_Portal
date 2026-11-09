"""
Celery tasks for asynchronous code execution and evaluation.

Handles compilation, execution, and result processing in background.
"""

import logging
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from django.db import transaction

from .models import CodeSubmission, TestCaseVerdict, ExecutionLog
from .execution_service import DockerExecutionService, ComparisonService
from questions.models import TestCase as QuestionTestCase

logger = logging.getLogger(__name__)


def _update_submitted_assignment_score(assignment_id):
    """Refresh marks after a late evaluation completes an already-submitted assignment."""
    from assessments.models import AssessmentAssignment
    from .services import SubmissionService

    assignment = AssessmentAssignment.objects.filter(id=assignment_id).first()
    if assignment and assignment.status == AssessmentAssignment.Status.SUBMITTED:
        try:
            SubmissionService.evaluate_assignment_submissions(assignment)
        except Exception:
            logger.exception(
                "Could not refresh marks for submitted assignment %s",
                assignment_id,
            )


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    time_limit=300  # 5 minutes hard limit
)
def execute_submission(self, submission_id: str, generation: int = None):
    """
    Execute a code submission against all test cases.

    Args:
        self: Celery task instance
        submission_id: UUID of CodeSubmission
        generation: submission generation this job is authorized to evaluate
    """
    try:
        submission = CodeSubmission.objects.get(id=submission_id)
    except CodeSubmission.DoesNotExist:
        logger.error(f"Submission {submission_id} not found")
        return {"error": "Submission not found"}

    execution_service = None
    working_dir = None
    generation = generation or submission.evaluation_generation
    task_id = str(self.request.id or "")

    if not settings.SERVER_DOCKER_EXECUTION_ENABLED:
        if submission.runner_type != CodeSubmission.RunnerType.SERVER_DOCKER:
            return {"submission_id": submission_id, "status": "client_runner_required"}
        with transaction.atomic():
            current = CodeSubmission.objects.select_for_update().get(id=submission_id)
            if current.evaluation_generation != generation:
                return {"submission_id": submission_id, "status": "superseded"}
            if current.status in {
                CodeSubmission.Status.PENDING,
                CodeSubmission.Status.COMPILING,
                CodeSubmission.Status.COMPILED,
                CodeSubmission.Status.EXECUTING,
            }:
                current.status = CodeSubmission.Status.FAILED
                current.verdict = CodeSubmission.Verdict.INTERNAL_ERROR
                current.compilation_error = (
                    "Server-side execution is disabled. Resubmit using a supported client runner."
                )
                current.execution_completed_at = timezone.now()
                current.save(update_fields=[
                    "status",
                    "verdict",
                    "compilation_error",
                    "execution_completed_at",
                    "updated_at",
                ])
        return {"submission_id": submission_id, "status": current.status}

    try:
        # Claim this generation. A duplicate delivery or a task superseded by
        # a faculty retry must not overwrite the newer evaluation.
        with transaction.atomic():
            current = CodeSubmission.objects.select_for_update().get(id=submission_id)
            if current.evaluation_generation != generation:
                return {"submission_id": submission_id, "status": "superseded"}
            is_celery_retry = (
                self.request.retries > 0
                and current.execution_job_id == task_id
                and current.status in {
                    CodeSubmission.Status.COMPILING,
                    CodeSubmission.Status.COMPILED,
                    CodeSubmission.Status.EXECUTING,
                }
            )
            if current.status != CodeSubmission.Status.PENDING and not is_celery_retry:
                return {"submission_id": submission_id, "status": "already_claimed"}
            current.status = CodeSubmission.Status.COMPILING
            current.execution_job_id = task_id
            current.execution_started_at = current.execution_started_at or timezone.now()
            current.save(update_fields=[
                "status",
                "execution_job_id",
                "execution_started_at",
                "updated_at",
            ])
            submission = current

        logger.info(f"Starting execution for submission {submission.id}")

        # Initialize Docker execution service
        execution_service = DockerExecutionService()

        # Create working directory
        working_dir = execution_service._create_execution_container()

        # === COMPILATION PHASE ===
        logger.debug(f"Compiling code for submission {submission.id}")

        compile_success, compile_error, compile_time = execution_service.compile_code(
            source_code=submission.source_code,
            working_dir=working_dir
        )

        submission.compilation_time_ms = int(compile_time)

        if not compile_success:
            # Compilation failed
            logger.warning(f"Compilation failed for submission {submission.id}")
            with transaction.atomic():
                current = CodeSubmission.objects.select_for_update().get(id=submission_id)
                if current.evaluation_generation != generation or current.execution_job_id != task_id:
                    return {"submission_id": submission_id, "status": "superseded"}
                current.status = CodeSubmission.Status.COMPLETED
                current.verdict = CodeSubmission.Verdict.COMPILATION_ERROR
                current.compilation_error = compile_error
                current.compilation_time_ms = int(compile_time)
                current.marks_obtained = 0
                current.total_test_cases = 0
                current.passed_test_cases = 0
                current.failed_test_cases = 0
                current.execution_completed_at = timezone.now()
                current.save()
                ExecutionLog.objects.create(
                    submission=current,
                    compilation_stderr=compile_error,
                    system_info={"status": "compilation_failed"},
                )
            logger.info(f"Submission {submission.id} failed compilation")
            _update_submitted_assignment_score(submission.assignment_id)

            return {
                "submission_id": str(submission.id),
                "verdict": CodeSubmission.Verdict.COMPILATION_ERROR,
                "error": compile_error
            }

        logger.info(f"Compilation successful for submission {submission.id}")

        # === EXECUTION PHASE ===
        updated = CodeSubmission.objects.filter(
            id=submission_id,
            evaluation_generation=generation,
            execution_job_id=task_id,
        ).update(status=CodeSubmission.Status.EXECUTING, updated_at=timezone.now())
        if not updated:
            return {"submission_id": submission_id, "status": "superseded"}
        submission.status = CodeSubmission.Status.EXECUTING

        # Get test cases for this question
        test_cases = QuestionTestCase.objects.filter(
            question=submission.question.question
        ).order_by("order")

        submission.total_test_cases = test_cases.count()
        submission.passed_test_cases = 0
        submission.failed_test_cases = 0

        total_execution_time = 0
        max_memory_used = 0.0
        test_verdicts = []

        logger.debug(f"Running {test_cases.count()} test cases for submission {submission.id}")

        # Run each test case
        for test_case in test_cases:
            logger.debug(f"Executing test case {test_case.order} for submission {submission.id}")

            # Execute with test case input
            execution_result = execution_service.execute_test_case(
                working_dir=working_dir,
                test_input=test_case.input,
                timeout_seconds=submission.question.question.time_limit_seconds
            )

            execution_status = execution_result["status"]
            actual_output = execution_result.get("output", "")
            error_message = execution_result.get("error", "")
            execution_time = execution_result.get("execution_time_ms", 0)

            total_execution_time += execution_time
            max_memory_used = max(max_memory_used, execution_result.get("memory_used_mb", 0))

            # Determine verdict
            if execution_status == "time_limit_exceeded":
                verdict_status = TestCaseVerdict.Status.TIME_LIMIT_EXCEEDED
                marks = 0

            elif execution_status == "memory_limit_exceeded":
                verdict_status = TestCaseVerdict.Status.MEMORY_LIMIT_EXCEEDED
                marks = 0

            elif execution_status == "runtime_error":
                verdict_status = TestCaseVerdict.Status.RUNTIME_ERROR
                marks = 0

            elif execution_status == "accepted":
                # Check output
                expected_output = test_case.expected_output

                if ComparisonService.compare_outputs(actual_output, expected_output):
                    verdict_status = TestCaseVerdict.Status.ACCEPTED
                    marks = test_case.marks
                    submission.passed_test_cases += 1

                else:
                    verdict_status = TestCaseVerdict.Status.WRONG_ANSWER
                    marks = 0

            else:
                verdict_status = TestCaseVerdict.Status.RUNTIME_ERROR
                marks = 0

            if verdict_status != TestCaseVerdict.Status.ACCEPTED:
                submission.failed_test_cases += 1

            # Record verdict
            test_verdict = {
                "submission": submission,
                "test_case_order": test_case.order,
                "is_sample": test_case.is_sample,
                "status": verdict_status,
                "marks_obtained": marks,
                "execution_time_ms": int(execution_time),
                "memory_used_mb": execution_result.get("memory_used_mb", 0),
                "expected_output": test_case.expected_output if test_case.is_sample else None,
                "actual_output": actual_output if test_case.is_sample else None,  # Don't store hidden test outputs
                "error_message": error_message if execution_status != "accepted" else None
            }

            test_verdicts.append(test_verdict)

            logger.debug(f"Test case {test_case.order}: {verdict_status} ({marks}/{test_case.marks} marks)")

        # === RESULTS PHASE ===
        logger.debug(f"Processing results for submission {submission.id}")

        # Calculate total marks
        total_marks = sum(t["marks_obtained"] for t in test_verdicts)
        submission.marks_obtained = total_marks

        # Determine final verdict
        if submission.passed_test_cases == submission.total_test_cases:
            submission.verdict = CodeSubmission.Verdict.ACCEPTED

        elif submission.failed_test_cases > 0:
            submission.verdict = CodeSubmission.Verdict.WRONG_ANSWER

        else:
            submission.verdict = CodeSubmission.Verdict.RUNTIME_ERROR

        submission.execution_time_ms = int(total_execution_time)
        submission.max_memory_used_mb = max_memory_used
        submission.status = CodeSubmission.Status.COMPLETED
        submission.execution_completed_at = timezone.now()

        # Save submission with all results
        with transaction.atomic():
            current = CodeSubmission.objects.select_for_update().get(id=submission_id)
            if current.evaluation_generation != generation or current.execution_job_id != task_id:
                return {"submission_id": submission_id, "status": "superseded"}
            current.compilation_time_ms = submission.compilation_time_ms
            current.total_test_cases = submission.total_test_cases
            current.passed_test_cases = submission.passed_test_cases
            current.failed_test_cases = submission.failed_test_cases
            current.marks_obtained = submission.marks_obtained
            current.verdict = submission.verdict
            current.execution_time_ms = submission.execution_time_ms
            current.max_memory_used_mb = submission.max_memory_used_mb
            current.status = CodeSubmission.Status.COMPLETED
            current.execution_completed_at = submission.execution_completed_at
            current.save()
            submission = current

            # Create test case verdicts
            for verdict_data in test_verdicts:
                verdict_data["submission"] = current
                TestCaseVerdict.objects.create(**verdict_data)

            # Create execution log
            ExecutionLog.objects.create(
                submission=submission,
                system_info={
                    "test_cases": submission.total_test_cases,
                    "passed": submission.passed_test_cases,
                    "failed": submission.failed_test_cases,
                    "total_time_ms": int(total_execution_time),
                    "max_memory_mb": max_memory_used
                }
            )

        logger.info(
            f"Submission {submission.id} completed: "
            f"{submission.passed_test_cases}/{submission.total_test_cases} tests passed, "
            f"{submission.marks_obtained} marks, verdict: {submission.verdict}"
        )
        _update_submitted_assignment_score(submission.assignment_id)

        return {
            "submission_id": str(submission.id),
            "verdict": submission.verdict,
            "marks": submission.marks_obtained,
            "passed": submission.passed_test_cases,
            "total": submission.total_test_cases
        }

    except CodeSubmission.DoesNotExist:
        logger.error(f"Submission {submission_id} not found during execution")
        return {"error": "Submission not found"}

    except Exception as e:
        logger.exception(f"Error executing submission {submission_id}: {e}")

        retries_exhausted = self.request.retries >= self.max_retries
        try:
            with transaction.atomic():
                current = CodeSubmission.objects.select_for_update().get(id=submission_id)
                if current.evaluation_generation != generation or current.execution_job_id != task_id:
                    return {"submission_id": submission_id, "status": "superseded"}
                if retries_exhausted:
                    current.status = CodeSubmission.Status.FAILED
                    current.verdict = CodeSubmission.Verdict.INTERNAL_ERROR
                    current.compilation_error = str(e)
                    current.execution_completed_at = timezone.now()
                    current.save(update_fields=[
                        "status",
                        "verdict",
                        "compilation_error",
                        "execution_completed_at",
                        "updated_at",
                    ])
                    ExecutionLog.objects.create(
                        submission=current,
                        system_info={"error": str(e)},
                    )
        except CodeSubmission.DoesNotExist:
            logger.error("Submission %s disappeared during task failure handling", submission_id)
            return {"error": "Submission not found"}
        except Exception as log_error:
            logger.exception(f"Error updating submission status: {log_error}")

        if retries_exhausted:
            logger.error("Evaluation retries exhausted for submission %s", submission_id)
            return {"submission_id": submission_id, "status": CodeSubmission.Status.FAILED}

        logger.warning(
            "Submission %s will remain in progress while Celery retries (%s/%s)",
            submission_id,
            self.request.retries + 1,
            self.max_retries,
        )
        raise self.retry(exc=e, countdown=min(2 ** self.request.retries * 60, 300))

    finally:
        # Always clean up
        if execution_service and working_dir:
            try:
                execution_service.cleanup(working_dir)
                logger.debug(f"Cleaned up working directory {working_dir}")
            except Exception as e:
                logger.error(f"Error cleaning up working directory: {e}")

        # Clean old containers periodically.
        task_id = str(self.request.id or "")
        if execution_service and task_id and int(task_id.replace("-", "")[-1], 16) % 10 == 0:
            try:
                execution_service.cleanup_old_containers()
            except Exception as e:
                logger.warning(f"Error cleaning old containers: {e}")


@shared_task
def update_submission_from_assignment(assignment_id: str):
    """
    Update assignment evaluation when all submissions are complete.

    Args:
        assignment_id: UUID of AssessmentAssignment
    """
    from assessments.models import AssessmentAssignment
    from .services import SubmissionService

    try:
        assignment = AssessmentAssignment.objects.get(id=assignment_id)
    except AssessmentAssignment.DoesNotExist:
        logger.warning(f"Assignment {assignment_id} not found")
        return

    try:
        # Get all submissions for this assignment
        service = SubmissionService()
        service.evaluate_assignment_submissions(assignment)

        logger.info(f"Updated evaluation for assignment {assignment_id}")

    except Exception as e:
        logger.exception(f"Error updating assignment evaluation: {e}")


@shared_task
def cleanup_old_submissions(days: int = 90):
    """
    Clean up old submission data.

    Args:
        days: Number of days to keep
    """
    from django.utils import timezone
    from datetime import timedelta

    try:
        cutoff_date = timezone.now() - timedelta(days=days)

        # Delete old submissions (keep audit trail, just delete code and logs)
        old_count = CodeSubmission.objects.filter(
            created_at__lt=cutoff_date
        ).count()

        logger.info(f"Found {old_count} submissions older than {days} days")

        # Note: In production, might want to archive instead of delete

    except Exception as e:
        logger.exception(f"Error cleaning up submissions: {e}")
