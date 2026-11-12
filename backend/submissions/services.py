"""
Services for submission management and evaluation.

Business logic for submissions, scoring, and result generation.
"""

import logging
from datetime import timedelta
from typing import Dict, List, Optional
from django.db import transaction
from django.utils import timezone

from .models import CodeSubmission, TestCaseVerdict, ExecutionLog
from assessments.models import AssessmentAssignment, AssessmentResult
from questions.models import TestCase

logger = logging.getLogger(__name__)

STALE_EVALUATION_AFTER = timedelta(minutes=10)
ACTIVE_EVALUATION_STATUSES = {
    CodeSubmission.Status.PENDING,
    CodeSubmission.Status.COMPILING,
    CodeSubmission.Status.COMPILED,
    CodeSubmission.Status.EXECUTING,
}


def is_stale_evaluation(submission, now=None):
    """Return whether an active evaluation has stopped updating for too long."""
    if submission.status not in ACTIVE_EVALUATION_STATUSES:
        return False
    now = now or timezone.now()
    return now - submission.updated_at >= STALE_EVALUATION_AFTER


class SubmissionService:
    """Service for submission management and evaluation."""

    @staticmethod
    def latest_submissions_by_question(assignment, question_ids=None):
        """Return the newest submission row for each assessment question."""
        queryset = CodeSubmission.objects.filter(assignment=assignment)
        if question_ids is not None:
            queryset = queryset.filter(question_id__in=question_ids)

        latest_by_question = {}
        for submission in queryset.order_by("question_id", "-created_at", "-id"):
            latest_by_question.setdefault(submission.question_id, submission)
        return latest_by_question

    @staticmethod
    def validate_submission_eligibility(
        student_id: str,
        assignment_id: str,
        question_id: str,
        allow_submission_grace: bool = False,
    ) -> tuple[bool, Optional[str]]:
        """
        Validate that student can submit for this question.

        Returns:
            Tuple of (is_eligible: bool, error_message: Optional[str])
        """
        try:
            assignment = AssessmentAssignment.objects.get(
                id=assignment_id,
                student_id=student_id
            )
        except AssessmentAssignment.DoesNotExist:
            return False, "Assignment not found or not assigned to you"

        # Code may only be submitted while the student is actively working.
        if assignment.status != AssessmentAssignment.Status.STARTED:
            return False, f"Cannot submit - assignment status is {assignment.status}"

        # Check the schedule, per-assignment deadline, and attempt duration.
        now = timezone.now()
        grace = timedelta(seconds=30) if allow_submission_grace else timedelta(0)
        deadline = assignment.effective_deadline()
        if not assignment.started_at or (
            deadline is not None and now > deadline + grace
        ):
            return False, "Deadline has passed"

        # Check if question exists in assessment
        try:
            from assessments.models import AssessmentQuestion
            AssessmentQuestion.objects.get(assessment=assignment.assessment, id=question_id)
        except AssessmentQuestion.DoesNotExist:
            return False, "Question not found in this assessment"

        return True, None

    @staticmethod
    def create_submission(
        student_id: str,
        assignment_id: str,
        question_id: str,
        source_code: str,
        ip_address: Optional[str] = None,
        allow_submission_grace: bool = False,
    ) -> tuple[CodeSubmission, Optional[str]]:
        """
        Create a code submission.

        Returns:
            Tuple of (submission: CodeSubmission, error: Optional[str])
        """
        # Validate eligibility
        is_eligible, error = SubmissionService.validate_submission_eligibility(
            student_id, assignment_id, question_id, allow_submission_grace
        )

        if not is_eligible:
            return None, error

        try:
            with transaction.atomic():
                assignment = AssessmentAssignment.objects.select_for_update().get(
                    id=assignment_id,
                    student_id=student_id,
                )
                # Coordinate submission creation with assessment finalization.
                is_eligible, error = SubmissionService.validate_submission_eligibility(
                    student_id,
                    assignment_id,
                    question_id,
                    allow_submission_grace,
                )
                if not is_eligible:
                    return None, error

                question = assignment.assessment.assessment_questions.get(id=question_id)

                # Count attempt while the assignment row is locked.
                attempt_number = CodeSubmission.objects.filter(
                    student_id=student_id,
                    question=question,
                    assignment=assignment
                ).count() + 1

                submission = CodeSubmission.objects.create(
                    assignment=assignment,
                    question=question,
                    student_id=student_id,
                    source_code=source_code,
                    language="c",
                    attempt_number=attempt_number,
                    ip_address=ip_address
                )

            logger.info(
                f"Created submission {submission.id} for student {student_id}, "
                f"question {question_id}, attempt {attempt_number}"
            )

            return submission, None

        except Exception as e:
            logger.exception(f"Error creating submission: {e}")
            return None, f"Error creating submission: {str(e)}"

    @staticmethod
    def get_submission_status(submission_id: str) -> Dict:
        """
        Get current status of a submission.

        Returns:
            Dict with status information
        """
        try:
            submission = CodeSubmission.objects.get(id=submission_id)

            status_data = {
                "id": str(submission.id),
                "status": submission.status,
                "verdict": submission.verdict,
                "marks_obtained": submission.marks_obtained,
                "compilation_error": submission.compilation_error,
                "total_test_cases": submission.total_test_cases,
                "passed_test_cases": submission.passed_test_cases,
                "failed_test_cases": submission.failed_test_cases,
                "compilation_time_ms": submission.compilation_time_ms,
                "execution_time_ms": submission.execution_time_ms,
                "max_memory_used_mb": submission.max_memory_used_mb,
                "execution_started_at": submission.execution_started_at,
                "execution_completed_at": submission.execution_completed_at,
            }

            if submission.status == CodeSubmission.Status.COMPLETED:
                result_data = SubmissionService.get_submission_result(
                    submission_id,
                    show_hidden=False,
                )
                status_data["test_case_verdicts"] = result_data.get(
                    "test_case_verdicts",
                    [],
                )

            return status_data

        except CodeSubmission.DoesNotExist:
            return {"error": "Submission not found"}

    @staticmethod
    def get_submission_result(submission_id: str, show_hidden: bool = False) -> Dict:
        """
        Get detailed result of a submission.

        Args:
            submission_id: Submission UUID
            show_hidden: Whether to show hidden test case details

        Returns:
            Dict with result information
        """
        try:
            submission = CodeSubmission.objects.get(id=submission_id)

            # Build result
            result = {
                "id": str(submission.id),
                "verdict": submission.verdict,
                "verdict_display": submission.get_verdict_display(),
                "marks_obtained": submission.marks_obtained,
                "total_test_cases": submission.total_test_cases,
                "passed_test_cases": submission.passed_test_cases,
                "success_rate": submission.get_success_rate(),
                "compilation_error": submission.compilation_error,
                "test_case_verdicts": []
            }

            # Get test case verdicts
            verdicts = TestCaseVerdict.objects.filter(
                submission=submission
            ).order_by("test_case_order")

            for verdict in verdicts:
                # Don't show details of hidden test cases to students
                if not show_hidden and not verdict.is_sample:
                    passed = verdict.status == TestCaseVerdict.Status.ACCEPTED
                    verdict_info = {
                        "test_case_order": verdict.test_case_order,
                        "is_sample": False,
                        "status": "accepted" if passed else "failed",
                        "status_display": "Passed" if passed else "Failed",
                    }
                else:
                    verdict_info = {
                        "test_case_order": verdict.test_case_order,
                        "is_sample": verdict.is_sample,
                        "status": verdict.status,
                        "marks_obtained": verdict.marks_obtained,
                        "execution_time_ms": verdict.execution_time_ms,
                        "memory_used_mb": verdict.memory_used_mb,
                        "expected_output": verdict.expected_output,
                        "actual_output": verdict.actual_output,
                        "error_message": verdict.error_message,
                    }

                result["test_case_verdicts"].append(verdict_info)

            return result

        except CodeSubmission.DoesNotExist:
            return {"error": "Submission not found"}

    @staticmethod
    @transaction.atomic
    def evaluate_assignment_submissions(assignment: AssessmentAssignment) -> None:
        """
        Evaluate the latest submission for each question and update marks.

        Args:
            assignment: AssessmentAssignment to evaluate
        """
        if assignment.status not in {
            AssessmentAssignment.Status.SUBMITTED,
            AssessmentAssignment.Status.GRADED,
        }:
            return

        question_ids = list(
            assignment.assessment.assessment_questions.values_list("id", flat=True)
        )
        if not question_ids:
            logger.warning("No questions found for assignment %s", assignment.id)
            return

        latest_by_question = SubmissionService.latest_submissions_by_question(
            assignment,
            question_ids,
        )

        pending_latest = [
            submission
            for submission in latest_by_question.values()
            if submission.status != CodeSubmission.Status.COMPLETED
        ]
        if pending_latest:
            logger.info(
                "Cannot evaluate assignment %s; %s latest submissions are not complete",
                assignment.id,
                len(pending_latest),
            )
            return

        latest_submissions = list(latest_by_question.values())
        marks_obtained = sum(submission.marks_obtained or 0 for submission in latest_submissions)
        passed_cases = sum(submission.passed_test_cases for submission in latest_submissions)
        total_cases = TestCase.objects.filter(
            question__assessment_questions__assessment_id=assignment.assessment_id,
        ).count()
        latest_completion = max(
            (
                submission.execution_completed_at or submission.created_at
                for submission in latest_submissions
            ),
            default=assignment.submitted_at or timezone.now(),
        )
        all_questions_submitted = set(latest_by_question) >= set(question_ids)
        # The active V2 Assessment model has no configurable pass-mark field.
        # An unanswered question earns zero and prevents a pass.
        passed = all_questions_submitted and total_cases > 0 and passed_cases == total_cases

        # A pending or failed latest submission must never fall back to an
        # older, higher-scoring submission for the same question.
        assignment.status = AssessmentAssignment.Status.GRADED
        assignment.save(update_fields=["status", "updated_at"])

        total_assessment_marks = assignment.assessment.total_marks
        percentage = (
            marks_obtained / total_assessment_marks * 100
            if total_assessment_marks
            else 0
        )
        result, created = AssessmentResult.objects.update_or_create(
            assessment=assignment.assessment,
            student=assignment.student,
            defaults={
                "total_marks_obtained": marks_obtained,
                "percentage": percentage,
                "passed": passed,
                "attempted_at": latest_completion,
                "feedback": (
                    "Based on the latest submission for each question. "
                    f"Passed {passed_cases}/{total_cases} test cases."
                ),
            }
        )

        logger.info(
            f"Updated assignment {assignment.id} with marks {marks_obtained}, "
            f"result {'created' if created else 'updated'}"
        )

    @staticmethod
    def get_student_submissions(
        student_id: str,
        assignment_id: Optional[str] = None,
        question_id: Optional[str] = None
    ) -> List[CodeSubmission]:
        """
        Get submissions for a student.

        Returns:
            List of submissions
        """
        queryset = CodeSubmission.objects.filter(student_id=student_id)

        if assignment_id:
            queryset = queryset.filter(assignment_id=assignment_id)

        if question_id:
            queryset = queryset.filter(question_id=question_id)

        return queryset.order_by("-created_at")

    @staticmethod
    def get_assessment_submissions(assignment_id: str) -> List[CodeSubmission]:
        """
        Get all submissions for an assessment assignment.

        Returns:
            List of submissions
        """
        return CodeSubmission.objects.filter(
            assignment_id=assignment_id
        ).order_by("-created_at")


class SubmissionSecurityService:
    """Service for security validation of submissions."""

    # Dangerous patterns that might indicate malicious code
    DANGEROUS_PATTERNS = [
        "system(",
        "exec(",
        "fork(",
        "popen(",
        "__builtin_",
        "asm(",
        "inline asm",
        "dlopen(",
        "dlsym(",
    ]

    @staticmethod
    def validate_source_code(source_code: str, strict: bool = False) -> tuple[bool, Optional[str]]:
        """
        Validate source code for security issues.

        Args:
            source_code: C source code to validate
            strict: Use strict validation

        Returns:
            Tuple of (is_valid: bool, error_message: Optional[str])
        """
        if not source_code or len(source_code) == 0:
            return False, "Source code cannot be empty"

        if len(source_code) > 100000:  # 100KB limit
            return False, "Source code too large (max 100KB)"

        # Check for dangerous patterns
        source_lower = source_code.lower()

        for pattern in SubmissionSecurityService.DANGEROUS_PATTERNS:
            if pattern.lower() in source_lower:
                return False, f"Source code contains restricted pattern: {pattern}"

        # Check for basic syntax
        if "#include" not in source_code:
            return False, "Code must include necessary headers"

        return True, None

    @staticmethod
    def get_code_statistics(source_code: str) -> Dict:
        """
        Get statistics about source code.

        Returns:
            Dict with code statistics
        """
        lines = source_code.split("\n")
        non_empty_lines = [l for l in lines if l.strip()]
        comment_lines = [l for l in lines if l.strip().startswith("//")]

        return {
            "total_lines": len(lines),
            "non_empty_lines": len(non_empty_lines),
            "comment_lines": len(comment_lines),
            "char_count": len(source_code),
        }
