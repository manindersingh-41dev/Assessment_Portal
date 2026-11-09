"""
Submission and Result Management for Geeta University Coding Assessment Portal.

Handles submission tracking, result calculation, and assessment evaluation.
"""

import logging
from typing import Dict, List, Optional, Tuple
from django.db import transaction
from django.utils import timezone
from django.db.models import Q, Sum, Count, Avg, F, Case, When, Value
from decimal import Decimal

from submissions.models import CodeSubmission, TestCaseVerdict
from submissions.services import is_stale_evaluation
from assessments.models import Assessment, AssessmentAssignment, AssessmentQuestion, AssessmentResult
from questions.models import Question

logger = logging.getLogger(__name__)


class ResultCalculationService:
    """Service for calculating assessment results."""

    @staticmethod
    def calculate_marks_for_submission(submission: CodeSubmission) -> Tuple[int, str]:
        """
        Calculate total marks for a submission based on test case verdicts.

        Args:
            submission: CodeSubmission to calculate marks for

        Returns:
            Tuple of (total_marks: int, verdict: str)
        """
        if submission.status != CodeSubmission.Status.COMPLETED:
            return 0, CodeSubmission.Verdict.NOT_EVALUATED

        # Get all test case verdicts
        verdicts = TestCaseVerdict.objects.filter(submission=submission)

        if not verdicts.exists():
            if submission.verdict == CodeSubmission.Verdict.COMPILATION_ERROR:
                return 0, CodeSubmission.Verdict.COMPILATION_ERROR
            return 0, CodeSubmission.Verdict.NOT_EVALUATED

        # Sum marks from accepted test cases
        total_marks = verdicts.filter(
            status=TestCaseVerdict.Status.ACCEPTED
        ).aggregate(total=Sum('marks_obtained'))['total'] or 0

        # Determine verdict
        if submission.verdict == CodeSubmission.Verdict.ACCEPTED:
            verdict = CodeSubmission.Verdict.ACCEPTED
        elif submission.verdict == CodeSubmission.Verdict.WRONG_ANSWER:
            verdict = CodeSubmission.Verdict.WRONG_ANSWER
        elif submission.verdict == CodeSubmission.Verdict.COMPILATION_ERROR:
            verdict = CodeSubmission.Verdict.COMPILATION_ERROR
        elif submission.verdict == CodeSubmission.Verdict.RUNTIME_ERROR:
            verdict = CodeSubmission.Verdict.RUNTIME_ERROR
        elif submission.verdict == CodeSubmission.Verdict.TIME_LIMIT_EXCEEDED:
            verdict = CodeSubmission.Verdict.TIME_LIMIT_EXCEEDED
        elif submission.verdict == CodeSubmission.Verdict.MEMORY_LIMIT_EXCEEDED:
            verdict = CodeSubmission.Verdict.MEMORY_LIMIT_EXCEEDED
        else:
            verdict = CodeSubmission.Verdict.NOT_EVALUATED

        return int(total_marks), verdict

    @staticmethod
    def get_latest_submission(
        assignment: AssessmentAssignment,
        question: AssessmentQuestion
    ) -> Optional[CodeSubmission]:
        """
        Get the latest submission for a question in an assignment.

        Args:
            assignment: AssessmentAssignment
            question: AssessmentQuestion

        Returns:
            Latest CodeSubmission or None
        """
        return CodeSubmission.objects.filter(
            assignment=assignment,
            question=question,
        ).order_by('-attempt_number', '-created_at', '-id').first()

    @staticmethod
    def get_best_submission(
        assignment: AssessmentAssignment,
        question: AssessmentQuestion
    ) -> Optional[CodeSubmission]:
        """Compatibility alias for the latest-submission policy."""
        return ResultCalculationService.get_latest_submission(assignment, question)

    @staticmethod
    def calculate_question_marks(
        assignment: AssessmentAssignment,
        question: AssessmentQuestion
    ) -> Tuple[int, int, str]:
        """
        Calculate marks for a question in an assignment.

        Args:
            assignment: AssessmentAssignment
            question: AssessmentQuestion

        Returns:
            Tuple of (marks_obtained: int, total_marks: int, verdict: str)
        """
        latest_submission = ResultCalculationService.get_latest_submission(assignment, question)

        if not latest_submission:
            return 0, question.marks, CodeSubmission.Verdict.NOT_EVALUATED

        # The latest attempt is authoritative even when it scores less than an
        # earlier attempt. Non-completed attempts receive zero until evaluated.
        marks, verdict = ResultCalculationService.calculate_marks_for_submission(latest_submission)

        return marks, question.marks, verdict

    @staticmethod
    def calculate_assignment_results(assignment: AssessmentAssignment) -> Dict:
        """
        Calculate complete results for an assignment.

        Args:
            assignment: AssessmentAssignment

        Returns:
            Dict with detailed results
        """
        assessment = assignment.assessment
        questions = assessment.questions.all().order_by('question_order')

        total_marks_obtained = 0
        total_marks = 0
        question_results = []
        attempted_questions = 0

        for question in questions:
            marks_obtained, question_total, verdict = ResultCalculationService.calculate_question_marks(
                assignment, question
            )

            total_marks_obtained += marks_obtained
            total_marks += question_total

            if verdict != CodeSubmission.Verdict.NOT_EVALUATED:
                attempted_questions += 1

            question_results.append({
                'question_id': str(question.id),
                'question_title': question.question.title,
                'question_order': question.question_order,
                'marks_obtained': marks_obtained,
                'total_marks': question_total,
                'verdict': verdict,
                'percentage': (marks_obtained / question_total * 100) if question_total > 0 else 0
            })

        # Calculate percentage
        percentage = (total_marks_obtained / total_marks * 100) if total_marks > 0 else 0

        # Determine pass/fail
        passed = total_marks > 0 and total_marks_obtained >= total_marks

        results = {
            'assignment_id': str(assignment.id),
            'student_id': str(assignment.student.id),
            'student_name': assignment.student.get_full_name(),
            'student_email': assignment.student.email,
            'assessment_id': str(assessment.id),
            'assessment_title': assessment.title,
            'total_marks_obtained': total_marks_obtained,
            'total_marks': total_marks,
            'percentage': round(percentage, 2),
            'passed': passed,
            'attempted_questions': attempted_questions,
            'total_questions': questions.count(),
            'question_results': question_results,
            'evaluated_at': timezone.now()
        }

        return results

    @staticmethod
    def calculate_test_case_stats(question: AssessmentQuestion) -> Dict:
        """
        Calculate test case statistics for a question.

        Args:
            question: AssessmentQuestion

        Returns:
            Dict with statistics
        """
        # Get all submissions for this question across all assessments
        submissions = CodeSubmission.objects.filter(question=question)

        total_submissions = submissions.count()
        accepted_submissions = submissions.filter(verdict=CodeSubmission.Verdict.ACCEPTED).count()
        wrong_answer = submissions.filter(verdict=CodeSubmission.Verdict.WRONG_ANSWER).count()
        compilation_error = submissions.filter(verdict=CodeSubmission.Verdict.COMPILATION_ERROR).count()
        runtime_error = submissions.filter(verdict=CodeSubmission.Verdict.RUNTIME_ERROR).count()

        average_marks = submissions.filter(
            marks_obtained__isnull=False
        ).aggregate(avg=Avg('marks_obtained'))['avg'] or 0

        acceptance_rate = (accepted_submissions / total_submissions * 100) if total_submissions > 0 else 0

        return {
            'total_submissions': total_submissions,
            'accepted': accepted_submissions,
            'wrong_answer': wrong_answer,
            'compilation_error': compilation_error,
            'runtime_error': runtime_error,
            'average_marks': round(float(average_marks), 2),
            'acceptance_rate': round(acceptance_rate, 2)
        }


class AssessmentEvaluationService:
    """Service for evaluating complete assessments."""

    @staticmethod
    def evaluate_assessment(assessment: Assessment) -> Dict:
        """
        Evaluate all submissions for an assessment.

        Args:
            assessment: Assessment to evaluate

        Returns:
            Dict with evaluation results
        """
        assignments = AssessmentAssignment.objects.filter(
            assessment=assessment,
            status=AssessmentAssignment.Status.SUBMITTED
        )

        evaluation_results = []
        total_students = assignments.count()
        passed_count = 0

        with transaction.atomic():
            for assignment in assignments:
                # Calculate results
                results = ResultCalculationService.calculate_assignment_results(assignment)

                if results['passed']:
                    passed_count += 1

                # Update assignment
                assignment.marks_obtained = results['total_marks_obtained']
                assignment.passed = results['passed']
                assignment.status = AssessmentAssignment.Status.GRADED
                assignment.save()

                # Create or update result
                result, created = AssessmentResult.objects.update_or_create(
                    assessment=assessment,
                    student=assignment.student,
                    defaults={
                        'total_marks_obtained': results['total_marks_obtained'],
                        'percentage': results['percentage'],
                        'passed': results['passed'],
                        'attempted_at': assignment.submitted_at or timezone.now(),
                        'feedback': f"Passed {results['attempted_questions']}/{results['total_questions']} questions. "
                                   f"Score: {results['total_marks_obtained']}/{results['total_marks']}"
                    }
                )

                evaluation_results.append(results)

        pass_rate = (passed_count / total_students * 100) if total_students > 0 else 0

        summary = {
            'assessment_id': str(assessment.id),
            'assessment_title': assessment.title,
            'total_students': total_students,
            'passed': passed_count,
            'failed': total_students - passed_count,
            'pass_rate': round(pass_rate, 2),
            'results': evaluation_results
        }

        logger.info(f"Evaluated assessment {assessment.id}: {passed_count}/{total_students} passed")

        return summary

    @staticmethod
    def get_assessment_statistics(assessment: Assessment) -> Dict:
        """
        Get statistics for an assessment.

        Args:
            assessment: Assessment

        Returns:
            Dict with statistics
        """
        results = AssessmentResult.objects.filter(assessment=assessment)
        assignments = AssessmentAssignment.objects.filter(assessment=assessment)

        total_students = assignments.count()
        evaluated_count = results.count()
        passed_count = results.filter(passed=True).count()

        avg_percentage = results.aggregate(avg=Avg('percentage'))['avg'] or 0
        avg_marks = results.aggregate(avg=Avg('total_marks_obtained'))['avg'] or 0

        # Question-wise statistics
        question_stats = {}
        for question in assessment.questions.all():
            stats = ResultCalculationService.calculate_test_case_stats(question)
            question_stats[str(question.id)] = {
                'title': question.question.title,
                'order': question.question_order,
                'marks': question.marks,
                'statistics': stats
            }

        return {
            'assessment_id': str(assessment.id),
            'assessment_title': assessment.title,
            'total_students': total_students,
            'evaluated': evaluated_count,
            'pending': total_students - evaluated_count,
            'passed': passed_count,
            'failed': evaluated_count - passed_count,
            'pass_rate': (passed_count / evaluated_count * 100) if evaluated_count > 0 else 0,
            'average_percentage': round(float(avg_percentage), 2),
            'average_marks': round(float(avg_marks), 2),
            'question_statistics': question_stats
        }


class SubmissionAggregationService:
    """Service for aggregating submission data."""

    @staticmethod
    def get_student_submissions(
        student_id: str,
        assignment_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Get submission history for a student.

        Args:
            student_id: Student UUID
            assignment_id: Optional assignment filter

        Returns:
            List of submission summaries
        """
        submissions = CodeSubmission.objects.filter(student_id=student_id).select_related(
            'assignment__assessment', 'question__question'
        )

        if assignment_id:
            submissions = submissions.filter(assignment_id=assignment_id)

        submissions = submissions.order_by('-created_at')

        result = []
        for submission in submissions:
            result.append({
                'id': str(submission.id),
                'assessment_title': submission.assignment.assessment.title,
                'question_title': submission.question.question.title,
                'question_order': submission.question.order,
                'status': submission.status,
                'status_display': submission.get_status_display(),
                'verdict': submission.verdict,
                'verdict_display': submission.get_verdict_display(),
                'marks_obtained': submission.marks_obtained,
                'total_test_cases': submission.total_test_cases,
                'passed_test_cases': submission.passed_test_cases,
                'attempt_number': submission.attempt_number,
                'created_at': submission.created_at.isoformat()
            })

        return result

    @staticmethod
    def get_assessment_submissions(
        assessment_id: Optional[str] = None,
        faculty_id: Optional[str] = None,
    ) -> List[Dict]:
        """
        Get all submissions for an assessment.

        Args:
            assessment_id: Assessment UUID

        Returns:
            List of submission summaries
        """
        submissions = CodeSubmission.objects.select_related(
            'assignment__assessment', 'student', 'question__question'
        ).order_by('-created_at')
        if assessment_id:
            submissions = submissions.filter(assignment__assessment_id=assessment_id)
        elif faculty_id:
            submissions = submissions.filter(assignment__assessment__created_by_id=faculty_id)
        else:
            return []

        result = []
        for submission in submissions:
            result.append({
                'id': str(submission.id),
                'assessment_id': str(submission.assignment.assessment_id),
                'assessment_title': submission.assignment.assessment.title,
                'student_name': submission.student.get_full_name(),
                'student_email': submission.student.email,
                'question_title': submission.question.question.title,
                'question_order': submission.question.order,
                'status': submission.status,
                'status_display': submission.get_status_display(),
                'verdict': submission.verdict,
                'verdict_display': submission.get_verdict_display(),
                'marks_obtained': submission.marks_obtained,
                'total_test_cases': submission.total_test_cases,
                'passed_test_cases': submission.passed_test_cases,
                'attempt_number': submission.attempt_number,
                'created_at': submission.created_at.isoformat()
            })

        return result

    @staticmethod
    def get_assignment_scorecard(assignment: AssessmentAssignment) -> Dict:
        """Aggregate each question's latest submission, regardless of its score."""
        questions = list(
            AssessmentQuestion.objects.filter(assessment=assignment.assessment)
            .select_related('question')
            .order_by('order', 'created_at')
        )
        submissions = list(
            CodeSubmission.objects.filter(assignment=assignment)
            .select_related('question', 'question__question')
            .order_by('attempt_number', 'created_at', 'id')
        )
        submissions_by_question = {}
        for submission in submissions:
            submissions_by_question.setdefault(str(submission.question_id), []).append(submission)

        question_results = []
        total_marks_obtained = 0
        total_test_cases = 0
        passed_test_cases = 0
        now = timezone.now()
        has_pending_submissions = any(
            submission.status not in {CodeSubmission.Status.COMPLETED, CodeSubmission.Status.FAILED}
            for question_submissions in submissions_by_question.values()
            for submission in question_submissions[-1:]
        )
        missing_question_submission = False
        failed_question_without_result = False

        for question in questions:
            question_submissions = submissions_by_question.get(str(question.id), [])
            latest_submission = question_submissions[-1] if question_submissions else None
            if not question_submissions:
                missing_question_submission = True
            elif latest_submission.status == CodeSubmission.Status.FAILED:
                failed_question_without_result = True

            marks = (
                min(int(latest_submission.marks_obtained or 0), question.marks)
                if latest_submission and latest_submission.status == CodeSubmission.Status.COMPLETED
                else 0
            )
            total_marks_obtained += marks
            test_case_source = latest_submission
            question_total_cases = test_case_source.total_test_cases if test_case_source else 0
            question_passed_cases = test_case_source.passed_test_cases if test_case_source else 0
            total_test_cases += question_total_cases
            passed_test_cases += question_passed_cases
            question_results.append({
                'question_id': str(question.id),
                'question_title': question.question.title,
                'question_order': question.order,
                'marks_obtained': marks,
                'total_marks': question.marks,
                'passed_test_cases': question_passed_cases,
                'total_test_cases': question_total_cases,
                'status': latest_submission.status if latest_submission else 'not_submitted',
                'verdict': latest_submission.verdict if latest_submission else CodeSubmission.Verdict.NOT_EVALUATED,
                'submission_id': str(latest_submission.id) if latest_submission else None,
                'submission_updated_at': latest_submission.updated_at if latest_submission else None,
                'evaluation_generation': latest_submission.evaluation_generation if latest_submission else None,
                'is_stale': is_stale_evaluation(latest_submission, now) if latest_submission else False,
            })

        # The marks attached to each assessment question are the scorecard's
        # source of truth, even if the cached assessment total is stale.
        total_marks = sum(question.marks for question in questions)
        percentage = round(total_marks_obtained * 100 / total_marks, 2) if total_marks else 0
        if assignment.status in {AssessmentAssignment.Status.ASSIGNED, AssessmentAssignment.Status.STARTED}:
            result_status = 'in_progress'
        elif has_pending_submissions:
            result_status = 'processing'
        elif missing_question_submission:
            result_status = 'incomplete'
        elif failed_question_without_result:
            result_status = 'evaluation_failed'
        else:
            result_status = 'evaluated'

        return {
            'id': str(assignment.id),
            'assignment_id': str(assignment.id),
            'assessment_id': str(assignment.assessment_id),
            'assessment_title': assignment.assessment.title,
            'student_name': assignment.student.get_full_name(),
            'student_email': assignment.student.email,
            'total_marks': total_marks,
            'marks_obtained': total_marks_obtained,
            'percentage': percentage,
            'passed_test_cases': passed_test_cases,
            'total_test_cases': total_test_cases,
            'status': result_status,
            'submitted_at': assignment.submitted_at,
            'question_results': question_results,
        }

    @staticmethod
    def get_question_submissions(
        question_id: str,
        assessment_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Get submissions for a specific question.

        Args:
            question_id: Question UUID
            assessment_id: Optional assessment filter

        Returns:
            List of submissions
        """
        submissions = CodeSubmission.objects.filter(question_id=question_id)

        if assessment_id:
            submissions = submissions.filter(assignment__assessment_id=assessment_id)

        submissions = submissions.order_by('-marks_obtained', '-created_at')

        result = []
        for submission in submissions:
            result.append({
                'id': str(submission.id),
                'student_name': submission.student.get_full_name(),
                'student_email': submission.student.email,
                'status': submission.status,
                'verdict': submission.verdict,
                'marks_obtained': submission.marks_obtained,
                'total_test_cases': submission.total_test_cases,
                'passed_test_cases': submission.passed_test_cases,
                'created_at': submission.created_at.isoformat()
            })

        return result


class ResultExportService:
    """Service for exporting results in various formats."""

    @staticmethod
    def prepare_assessment_results(assessment_id: str) -> List[Dict]:
        """
        Prepare assessment results for export.

        Args:
            assessment_id: Assessment UUID

        Returns:
            List of result dictionaries suitable for CSV/Excel export
        """
        assessment = Assessment.objects.get(id=assessment_id)
        results = AssessmentResult.objects.filter(assessment=assessment)

        export_data = []

        for result in results:
            # Get assignment to find question-wise marks
            assignment = AssessmentAssignment.objects.get(
                assessment=assessment,
                student=result.student
            )

            row = {
                'student_name': result.student.get_full_name(),
                'student_email': result.student.email(),
                'total_marks': result.total_marks_obtained,
                'passing_marks': assessment.passing_marks,
                'percentage': result.percentage,
                'status': 'Passed' if result.passed else 'Failed'
            }

            # Add question-wise marks
            for question in assessment.questions.all().order_by('question_order'):
                marks, _, _ = ResultCalculationService.calculate_question_marks(assignment, question)
                row[f"Q{question.question_order}"] = marks

            export_data.append(row)

        return export_data

    @staticmethod
    def get_csv_headers(assessment_id: str) -> List[str]:
        """
        Get CSV headers for assessment results.

        Args:
            assessment_id: Assessment UUID

        Returns:
            List of header names
        """
        assessment = Assessment.objects.get(id=assessment_id)

        headers = ['Student Name', 'Student Email', 'Total Marks', 'Passing Marks', 'Percentage', 'Status']

        # Add question headers
        for question in assessment.questions.all().order_by('question_order'):
            headers.append(f"Q{question.question_order} ({question.marks})")

        return headers

    @staticmethod
    def prepare_question_statistics(question_id: str) -> Dict:
        """
        Prepare question statistics for export.

        Args:
            question_id: Question UUID

        Returns:
            Dict with statistics data
        """
        submissions = CodeSubmission.objects.filter(question_id=question_id)

        stats = {
            'question_id': question_id,
            'total_submissions': submissions.count(),
            'accepted': submissions.filter(verdict=CodeSubmission.Verdict.ACCEPTED).count(),
            'wrong_answer': submissions.filter(verdict=CodeSubmission.Verdict.WRONG_ANSWER).count(),
            'compilation_error': submissions.filter(verdict=CodeSubmission.Verdict.COMPILATION_ERROR).count(),
            'runtime_error': submissions.filter(verdict=CodeSubmission.Verdict.RUNTIME_ERROR).count(),
            'time_limit_exceeded': submissions.filter(
                verdict=CodeSubmission.Verdict.TIME_LIMIT_EXCEEDED
            ).count(),
            'memory_limit_exceeded': submissions.filter(
                verdict=CodeSubmission.Verdict.MEMORY_LIMIT_EXCEEDED
            ).count(),
            'internal_error': submissions.filter(verdict=CodeSubmission.Verdict.INTERNAL_ERROR).count(),
        }

        return stats
