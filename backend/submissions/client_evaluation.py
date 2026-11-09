"""Shared persistence and judging for client-side code runners."""

import hashlib
import json

from django.db import IntegrityError, transaction
from django.utils import timezone

from assessments.models import AssessmentAssignment, AssessmentQuestion
from questions.models import TestCase as QuestionTestCase

from .execution_service import ComparisonService
from .models import CodeSubmission, ExecutionLog, TestCaseVerdict
from .services import SubmissionService

MAX_CLIENT_TEST_CASES = 250
MAX_CASE_SNAPSHOT_BYTES = 2 * 1024 * 1024


class ClientEvaluationError(Exception):
    """Expected client-evaluation rejection with an HTTP response status."""

    def __init__(self, detail, status_code=400):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def build_case_snapshot(assessment_question):
    """Capture the cases and scoring data that this submission will use."""
    question = assessment_question.question
    test_cases = list(
        QuestionTestCase.objects.filter(question=question).order_by("order", "created_at")
    )
    if not test_cases:
        raise ClientEvaluationError("This question does not have any test cases.")
    if len(test_cases) > MAX_CLIENT_TEST_CASES:
        raise ClientEvaluationError(
            f"This question has more than {MAX_CLIENT_TEST_CASES} test cases, "
            "which exceeds the client runner limit."
        )
    orders = [case.order for case in test_cases]
    if len(orders) != len(set(orders)):
        raise ClientEvaluationError(
            "This question has duplicate test-case order values. Ask faculty to correct the question."
        )

    snapshot_cases = []
    snapshot_size = 0
    for case in test_cases:
        case_snapshot = {
            "id": str(case.id),
            "order": case.order,
            "is_sample": case.is_sample,
            "input": case.input,
            "expected_output": case.expected_output,
            "marks": case.marks,
        }
        snapshot_size += len(case.input.encode("utf-8"))
        snapshot_size += len(case.expected_output.encode("utf-8"))
        snapshot_cases.append(case_snapshot)

    if snapshot_size > MAX_CASE_SNAPSHOT_BYTES:
        raise ClientEvaluationError(
            "The combined test inputs and expected outputs exceed the 2 MB client runner limit."
        )

    return {
        "question_id": str(assessment_question.id),
        "time_limit_seconds": question.time_limit_seconds,
        "memory_limit_mb": question.memory_limit_mb,
        "test_cases": snapshot_cases,
    }


def public_case_snapshot(assignment_id, snapshot):
    """Return execution inputs without exposing hidden expected outputs or marks."""
    public_cases = []
    for case in snapshot["test_cases"]:
        public_case = {
            "id": case["id"],
            "order": case["order"],
            "is_sample": case["is_sample"],
            "input": case["input"],
        }
        if case["is_sample"]:
            public_case["expected_output"] = case["expected_output"]
        public_cases.append(public_case)

    return {
        "assignment_id": str(assignment_id),
        "question_id": snapshot["question_id"],
        "time_limit_seconds": snapshot["time_limit_seconds"],
        "memory_limit_mb": snapshot["memory_limit_mb"],
        "test_cases": public_cases,
    }


def _request_hash(payload):
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class ClientEvaluationService:
    """Create pending client evaluations and judge their reported outcomes."""

    @staticmethod
    def create_pending_submission(student, payload, ip_address=None):
        client_submission_id = payload["client_submission_id"]
        request_hash = _request_hash(payload)

        existing = CodeSubmission.objects.filter(
            client_submission_id=client_submission_id
        ).first()
        if existing:
            if (
                existing.student_id != student.id
                or existing.client_request_sha256 != request_hash
            ):
                raise ClientEvaluationError(
                    "client_submission_id was already used with a different request.",
                    status_code=409,
                )
            return existing, False

        is_eligible, error = SubmissionService.validate_submission_eligibility(
            student_id=str(student.id),
            assignment_id=str(payload["assignment_id"]),
            question_id=str(payload["question_id"]),
            allow_submission_grace=True,
        )
        if not is_eligible:
            raise ClientEvaluationError(error or "This assignment cannot be submitted.")

        try:
            with transaction.atomic():
                assignment = AssessmentAssignment.objects.select_for_update().get(
                    id=payload["assignment_id"],
                    student=student,
                )
                # Recheck after acquiring the assignment lock so a concurrent
                # assessment finalization cannot race this submission start.
                is_eligible, error = SubmissionService.validate_submission_eligibility(
                    student_id=str(student.id),
                    assignment_id=str(assignment.id),
                    question_id=str(payload["question_id"]),
                    allow_submission_grace=True,
                )
                if not is_eligible:
                    raise ClientEvaluationError(
                        error or "This assignment cannot be submitted."
                    )

                assessment_question = AssessmentQuestion.objects.select_related(
                    "question"
                ).get(
                    id=payload["question_id"],
                    assessment_id=assignment.assessment_id,
                )
                snapshot = build_case_snapshot(assessment_question)
                attempt_number = CodeSubmission.objects.filter(
                    student=student,
                    assignment=assignment,
                    question=assessment_question,
                ).count() + 1
                submission = CodeSubmission.objects.create(
                    assignment=assignment,
                    question=assessment_question,
                    student=student,
                    source_code=payload["source_code"],
                    language="c",
                    status=CodeSubmission.Status.PENDING,
                    verdict=CodeSubmission.Verdict.NOT_EVALUATED,
                    attempt_number=attempt_number,
                    ip_address=ip_address,
                    runner_type=payload["runner_type"],
                    runner_version=payload["runner_version"],
                    compiler_version=payload.get("compiler_version", ""),
                    client_submission_id=client_submission_id,
                    client_request_sha256=request_hash,
                    client_test_cases_snapshot=snapshot,
                    execution_started_at=timezone.now(),
                )
                return submission, True
        except IntegrityError:
            # A concurrent retry may win the unique client_submission_id race.
            existing = CodeSubmission.objects.filter(
                client_submission_id=client_submission_id
            ).first()
            if existing and existing.student_id == student.id and existing.client_request_sha256 == request_hash:
                return existing, False
            if existing is None:
                raise
            raise ClientEvaluationError(
                "client_submission_id was already used with a different request.",
                status_code=409,
            )
        except AssessmentAssignment.DoesNotExist:
            raise ClientEvaluationError("Assignment not found or not assigned to you.", 404)
        except AssessmentQuestion.DoesNotExist:
            raise ClientEvaluationError("Question not found in this assessment.", 404)

    @staticmethod
    def complete_submission(submission_id, student, payload):
        canonical_payload = dict(payload)
        canonical_payload["test_results"] = sorted(
            payload["test_results"],
            key=lambda result: str(result["test_case_id"]),
        )
        request_hash = _request_hash(canonical_payload)
        with transaction.atomic():
            try:
                submission = CodeSubmission.objects.select_for_update().get(
                    id=submission_id,
                    student=student,
                )
            except CodeSubmission.DoesNotExist:
                raise ClientEvaluationError("Submission not found.", 404)

            if submission.runner_type == CodeSubmission.RunnerType.SERVER_DOCKER:
                raise ClientEvaluationError(
                    "This submission does not use a client-side runner.",
                    status_code=409,
                )

            if submission.client_results_sha256:
                if submission.client_results_sha256 == request_hash:
                    return submission, False
                raise ClientEvaluationError(
                    "This submission already has a different result report.",
                    status_code=409,
                )

            if submission.status != CodeSubmission.Status.PENDING:
                raise ClientEvaluationError(
                    "Only a pending client evaluation can receive results.",
                    status_code=409,
                )

            snapshot = submission.client_test_cases_snapshot or {}
            cases = snapshot.get("test_cases", [])
            if not cases:
                raise ClientEvaluationError(
                    "The saved execution case snapshot is unavailable. Submit the code again.",
                    status_code=409,
                )
            compilation = payload["compilation"]
            result_rows = payload["test_results"]

            if compilation["status"] == "success":
                expected_ids = {case["id"] for case in cases}
                submitted_ids = {str(result["test_case_id"]) for result in result_rows}
                if submitted_ids != expected_ids:
                    raise ClientEvaluationError(
                        "Successful compilation must report exactly one result for every test case.",
                    )
            elif result_rows:
                raise ClientEvaluationError(
                    "Test results must be empty when compilation fails."
                )

            results_by_id = {
                str(result["test_case_id"]): result
                for result in result_rows
            }
            verdict_rows = []
            total_execution_time = 0
            passed_count = 0
            failed_count = 0
            marks_obtained = 0
            observed_statuses = set()

            if compilation["status"] == "error":
                submission.status = CodeSubmission.Status.COMPLETED
                submission.verdict = CodeSubmission.Verdict.COMPILATION_ERROR
                submission.compilation_error = compilation["diagnostics"]
                submission.compilation_time_ms = compilation["duration_ms"]
                submission.total_test_cases = 0
                submission.passed_test_cases = 0
                submission.failed_test_cases = 0
                submission.marks_obtained = 0
                submission.execution_time_ms = 0
            else:
                for case in cases:
                    result = results_by_id[case["id"]]
                    execution_status = result["status"]
                    exit_code = result.get("exit_code")
                    actual_output = result["stdout"]
                    duration_ms = result["duration_ms"]

                    if execution_status == "time_limit_exceeded":
                        verdict = TestCaseVerdict.Status.TIME_LIMIT_EXCEEDED
                    elif execution_status == "memory_limit_exceeded":
                        verdict = TestCaseVerdict.Status.MEMORY_LIMIT_EXCEEDED
                    elif execution_status == "runtime_error" or exit_code not in (0, None):
                        verdict = TestCaseVerdict.Status.RUNTIME_ERROR
                    elif ComparisonService.compare_outputs(
                        actual_output,
                        case["expected_output"],
                    ):
                        verdict = TestCaseVerdict.Status.ACCEPTED
                    else:
                        verdict = TestCaseVerdict.Status.WRONG_ANSWER

                    case_marks = case["marks"] if verdict == TestCaseVerdict.Status.ACCEPTED else 0
                    if verdict == TestCaseVerdict.Status.ACCEPTED:
                        passed_count += 1
                        marks_obtained += case_marks
                    else:
                        failed_count += 1
                    observed_statuses.add(verdict)
                    total_execution_time += duration_ms

                    is_sample = case["is_sample"]
                    stderr = result["stderr"]
                    error_message = None
                    if is_sample and verdict != TestCaseVerdict.Status.ACCEPTED:
                        error_message = stderr or None

                    verdict_rows.append(TestCaseVerdict(
                        submission=submission,
                        test_case_order=case["order"],
                        is_sample=is_sample,
                        status=verdict,
                        marks_obtained=case_marks,
                        execution_time_ms=duration_ms,
                        memory_used_mb=None,
                        expected_output=case["expected_output"] if is_sample else None,
                        actual_output=actual_output if is_sample else None,
                        error_message=error_message,
                    ))

                if passed_count == len(cases):
                    overall_verdict = CodeSubmission.Verdict.ACCEPTED
                elif TestCaseVerdict.Status.TIME_LIMIT_EXCEEDED in observed_statuses:
                    overall_verdict = CodeSubmission.Verdict.TIME_LIMIT_EXCEEDED
                elif TestCaseVerdict.Status.MEMORY_LIMIT_EXCEEDED in observed_statuses:
                    overall_verdict = CodeSubmission.Verdict.MEMORY_LIMIT_EXCEEDED
                elif TestCaseVerdict.Status.RUNTIME_ERROR in observed_statuses:
                    overall_verdict = CodeSubmission.Verdict.RUNTIME_ERROR
                else:
                    overall_verdict = CodeSubmission.Verdict.WRONG_ANSWER

                submission.status = CodeSubmission.Status.COMPLETED
                submission.verdict = overall_verdict
                submission.compilation_error = None
                submission.compilation_time_ms = compilation["duration_ms"]
                submission.total_test_cases = len(cases)
                submission.passed_test_cases = passed_count
                submission.failed_test_cases = failed_count
                submission.marks_obtained = marks_obtained
                submission.execution_time_ms = total_execution_time
                TestCaseVerdict.objects.bulk_create(verdict_rows)

            completed_at = timezone.now()
            submission.execution_completed_at = completed_at
            submission.client_results_sha256 = request_hash
            submission.save(update_fields=[
                "status",
                "verdict",
                "compilation_error",
                "compilation_time_ms",
                "total_test_cases",
                "passed_test_cases",
                "failed_test_cases",
                "marks_obtained",
                "execution_time_ms",
                "execution_completed_at",
                "client_results_sha256",
                "updated_at",
            ])

            ExecutionLog.objects.update_or_create(
                submission=submission,
                defaults={
                    "compilation_stderr": compilation["diagnostics"],
                    "system_info": {
                        "runner_type": submission.runner_type,
                        "runner_version": submission.runner_version,
                        "compiler_version": submission.compiler_version,
                        "client_reported": True,
                        "test_cases": submission.total_test_cases,
                        "passed": submission.passed_test_cases,
                        "failed": submission.failed_test_cases,
                    },
                },
            )

            return submission, True
