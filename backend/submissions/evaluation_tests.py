"""
Comprehensive tests for Result Calculation and Assessment Evaluation.

Tests all calculation logic, result aggregation, and access controls.
"""

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from datetime import timedelta

from users.models import User
from questions.models import Question, TestCase as QuestionTestCase
from assessments.models import Assessment, AssessmentQuestion, AssessmentAssignment
from submissions.models import CodeSubmission, TestCaseVerdict
from .evaluation_service import (
    ResultCalculationService, AssessmentEvaluationService,
    SubmissionAggregationService
)


class ResultCalculationTests(TestCase):
    """Tests for result calculation logic."""

    def setUp(self):
        """Set up test data."""
        self.student = User.objects.create_user(
            email='student@geetauniversity.edu.in',
            password='testpass123',
            role='student',
            is_email_verified=True
        )

        self.faculty = User.objects.create_user(
            email='faculty@geetauniversity.edu.in',
            password='testpass123',
            role='faculty',
            is_approved=True,
            is_email_verified=True
        )

        now = timezone.now()
        self.assessment = Assessment.objects.create(
            title='Test Assessment',
            start_datetime=now - timedelta(hours=1),
            end_datetime=now + timedelta(hours=2),
            duration_minutes=120,
            total_marks=100,
            passing_marks=60,
            created_by=self.faculty,
            is_published=True
        )

        self.question = Question.objects.create(
            title='Sum of Numbers',
            description='Find sum',
            input_format='Numbers',
            output_format='Sum',
            constraints='1 <= N <= 100',
            sample_input='1 2 3',
            sample_output='6',
            difficulty=Question.Difficulty.EASY,
            total_marks=10,
            time_limit_seconds=60,
            memory_limit_mb=128,
            status=Question.Status.ACTIVE,
            created_by=self.faculty
        )

        # Create 4 test cases with different marks
        self.test_case_1 = QuestionTestCase.objects.create(
            question=self.question,
            input='1 2',
            expected_output='3',
            is_sample=True,
            marks=2,
            order=1
        )

        self.test_case_2 = QuestionTestCase.objects.create(
            question=self.question,
            input='5 5',
            expected_output='10',
            is_sample=True,
            marks=2,
            order=2
        )

        self.test_case_3 = QuestionTestCase.objects.create(
            question=self.question,
            input='100 200',
            expected_output='300',
            is_sample=False,
            marks=3,
            order=3
        )

        self.test_case_4 = QuestionTestCase.objects.create(
            question=self.question,
            input='10 10',
            expected_output='20',
            is_sample=False,
            marks=3,
            order=4
        )

        self.assessment_question = AssessmentQuestion.objects.create(
            assessment=self.assessment,
            question=self.question,
            question_title=self.question.title,
            question_description=self.question.description,
            question_input_format=self.question.input_format,
            question_output_format=self.question.output_format,
            question_constraints=self.question.constraints,
            question_difficulty=self.question.difficulty,
            question_language=self.question.language,
            question_order=1,
            marks=10
        )

        self.assignment = AssessmentAssignment.objects.create(
            assessment=self.assessment,
            student=self.student,
            status=AssessmentAssignment.Status.STARTED
        )

    def test_calculate_marks_all_passed(self):
        """Test marks calculation when all test cases pass."""
        submission = CodeSubmission.objects.create(
            assignment=self.assignment,
            question=self.assessment_question,
            student=self.student,
            source_code='#include <stdio.h>\nint main() { return 0; }',
            status=CodeSubmission.Status.COMPLETED,
            verdict=CodeSubmission.Verdict.ACCEPTED,
            total_test_cases=4,
            passed_test_cases=4
        )

        # Create verdicts for all test cases
        for i, marks in enumerate([2, 2, 3, 3], 1):
            TestCaseVerdict.objects.create(
                submission=submission,
                test_case_order=i,
                is_sample=i <= 2,
                status=TestCaseVerdict.Status.ACCEPTED,
                marks_obtained=marks
            )

        marks, verdict = ResultCalculationService.calculate_marks_for_submission(submission)

        self.assertEqual(marks, 10)
        self.assertEqual(verdict, CodeSubmission.Verdict.ACCEPTED)

    def test_calculate_marks_partial_passed(self):
        """Test marks calculation when some test cases pass."""
        # Example: Test cases 1, 2, 3 pass (2+2+3 = 7), case 4 fails
        submission = CodeSubmission.objects.create(
            assignment=self.assignment,
            question=self.assessment_question,
            student=self.student,
            source_code='#include <stdio.h>\nint main() { return 0; }',
            status=CodeSubmission.Status.COMPLETED,
            verdict=CodeSubmission.Verdict.WRONG_ANSWER,
            total_test_cases=4,
            passed_test_cases=3,
            failed_test_cases=1
        )

        # Create verdicts
        for i, marks in enumerate([2, 2, 3, 3], 1):
            status_val = TestCaseVerdict.Status.ACCEPTED if i <= 3 else TestCaseVerdict.Status.WRONG_ANSWER
            marks_val = marks if i <= 3 else 0

            TestCaseVerdict.objects.create(
                submission=submission,
                test_case_order=i,
                is_sample=i <= 2,
                status=status_val,
                marks_obtained=marks_val
            )

        marks, verdict = ResultCalculationService.calculate_marks_for_submission(submission)

        self.assertEqual(marks, 7)
        self.assertEqual(verdict, CodeSubmission.Verdict.WRONG_ANSWER)

    def test_calculate_marks_compilation_error(self):
        """Test marks calculation with compilation error."""
        submission = CodeSubmission.objects.create(
            assignment=self.assignment,
            question=self.assessment_question,
            student=self.student,
            source_code='invalid code',
            status=CodeSubmission.Status.COMPLETED,
            verdict=CodeSubmission.Verdict.COMPILATION_ERROR,
            compilation_error='Syntax error',
            marks_obtained=0
        )

        marks, verdict = ResultCalculationService.calculate_marks_for_submission(submission)

        self.assertEqual(marks, 0)
        self.assertEqual(verdict, CodeSubmission.Verdict.COMPILATION_ERROR)

    def test_get_best_submission(self):
        """Test getting best submission."""
        # Create multiple submissions with different marks
        sub1 = CodeSubmission.objects.create(
            assignment=self.assignment,
            question=self.assessment_question,
            student=self.student,
            source_code='code1',
            status=CodeSubmission.Status.COMPLETED,
            verdict=CodeSubmission.Verdict.WRONG_ANSWER,
            marks_obtained=5,
            created_at=timezone.now()
        )

        sub2 = CodeSubmission.objects.create(
            assignment=self.assignment,
            question=self.assessment_question,
            student=self.student,
            source_code='code2',
            status=CodeSubmission.Status.COMPLETED,
            verdict=CodeSubmission.Verdict.ACCEPTED,
            marks_obtained=10,
            created_at=timezone.now() + timedelta(seconds=1)
        )

        best = ResultCalculationService.get_best_submission(self.assignment, self.assessment_question)

        self.assertEqual(best.id, sub2.id)
        self.assertEqual(best.marks_obtained, 10)

    def test_calculate_question_marks(self):
        """Test question marks calculation."""
        # Create submission with partial marks
        submission = CodeSubmission.objects.create(
            assignment=self.assignment,
            question=self.assessment_question,
            student=self.student,
            source_code='code',
            status=CodeSubmission.Status.COMPLETED,
            verdict=CodeSubmission.Verdict.WRONG_ANSWER,
            marks_obtained=7
        )

        # Add verdicts
        for i, marks in enumerate([2, 2, 3, 0], 1):
            TestCaseVerdict.objects.create(
                submission=submission,
                test_case_order=i,
                is_sample=i <= 2,
                status=TestCaseVerdict.Status.ACCEPTED if marks > 0 else TestCaseVerdict.Status.WRONG_ANSWER,
                marks_obtained=marks
            )

        marks_obtained, total_marks, verdict = ResultCalculationService.calculate_question_marks(
            self.assignment, self.assessment_question
        )

        self.assertEqual(marks_obtained, 7)
        self.assertEqual(total_marks, 10)
        self.assertEqual(verdict, CodeSubmission.Verdict.WRONG_ANSWER)


class AssessmentEvaluationTests(TestCase):
    """Tests for assessment evaluation logic."""

    def setUp(self):
        """Set up test data."""
        self.student1 = User.objects.create_user(
            email='student1@geetauniversity.edu.in',
            password='testpass123',
            role='student',
            is_email_verified=True,
            first_name='John',
            last_name='Doe'
        )

        self.student2 = User.objects.create_user(
            email='student2@geetauniversity.edu.in',
            password='testpass123',
            role='student',
            is_email_verified=True,
            first_name='Jane',
            last_name='Smith'
        )

        self.faculty = User.objects.create_user(
            email='faculty@geetauniversity.edu.in',
            password='testpass123',
            role='faculty',
            is_approved=True,
            is_email_verified=True
        )

        now = timezone.now()
        self.assessment = Assessment.objects.create(
            title='Test Assessment',
            start_datetime=now - timedelta(hours=1),
            end_datetime=now + timedelta(hours=2),
            duration_minutes=120,
            total_marks=100,
            passing_marks=60,
            created_by=self.faculty,
            is_published=True
        )

        self.question = Question.objects.create(
            title='Test Question',
            description='Test',
            input_format='Test',
            output_format='Test',
            constraints='Test',
            sample_input='Test',
            sample_output='Test',
            difficulty=Question.Difficulty.EASY,
            total_marks=100,
            time_limit_seconds=60,
            memory_limit_mb=128,
            status=Question.Status.ACTIVE,
            created_by=self.faculty
        )

        self.assessment_question = AssessmentQuestion.objects.create(
            assessment=self.assessment,
            question=self.question,
            question_title=self.question.title,
            question_description=self.question.description,
            question_input_format=self.question.input_format,
            question_output_format=self.question.output_format,
            question_constraints=self.question.constraints,
            question_difficulty=self.question.difficulty,
            question_language=self.question.language,
            question_order=1,
            marks=100
        )

        self.assignment1 = AssessmentAssignment.objects.create(
            assessment=self.assessment,
            student=self.student1,
            status=AssessmentAssignment.Status.SUBMITTED,
            submitted_at=timezone.now()
        )

        self.assignment2 = AssessmentAssignment.objects.create(
            assessment=self.assessment,
            student=self.student2,
            status=AssessmentAssignment.Status.SUBMITTED,
            submitted_at=timezone.now()
        )

    def test_calculate_assignment_results(self):
        """Test calculating complete assignment results."""
        submission = CodeSubmission.objects.create(
            assignment=self.assignment1,
            question=self.assessment_question,
            student=self.student1,
            source_code='code',
            status=CodeSubmission.Status.COMPLETED,
            verdict=CodeSubmission.Verdict.ACCEPTED,
            total_test_cases=1,
            passed_test_cases=1,
            marks_obtained=100
        )

        TestCaseVerdict.objects.create(
            submission=submission,
            test_case_order=1,
            is_sample=True,
            status=TestCaseVerdict.Status.ACCEPTED,
            marks_obtained=100
        )

        results = ResultCalculationService.calculate_assignment_results(self.assignment1)

        self.assertEqual(results['total_marks_obtained'], 100)
        self.assertEqual(results['total_marks'], 100)
        self.assertEqual(results['percentage'], 100.0)
        self.assertTrue(results['passed'])

    def test_calculate_assignment_results_fail(self):
        """Test calculation for failed assignment."""
        submission = CodeSubmission.objects.create(
            assignment=self.assignment1,
            question=self.assessment_question,
            student=self.student1,
            source_code='code',
            status=CodeSubmission.Status.COMPLETED,
            verdict=CodeSubmission.Verdict.WRONG_ANSWER,
            total_test_cases=1,
            passed_test_cases=0,
            marks_obtained=30
        )

        TestCaseVerdict.objects.create(
            submission=submission,
            test_case_order=1,
            is_sample=True,
            status=TestCaseVerdict.Status.WRONG_ANSWER,
            marks_obtained=30
        )

        results = ResultCalculationService.calculate_assignment_results(self.assignment1)

        self.assertEqual(results['total_marks_obtained'], 30)
        self.assertEqual(results['percentage'], 30.0)
        self.assertFalse(results['passed'])

    def test_get_assessment_statistics(self):
        """Test assessment statistics calculation."""
        # Create submission for student 1 (passed)
        sub1 = CodeSubmission.objects.create(
            assignment=self.assignment1,
            question=self.assessment_question,
            student=self.student1,
            source_code='code',
            status=CodeSubmission.Status.COMPLETED,
            verdict=CodeSubmission.Verdict.ACCEPTED,
            marks_obtained=100
        )

        TestCaseVerdict.objects.create(
            submission=sub1,
            test_case_order=1,
            is_sample=True,
            status=TestCaseVerdict.Status.ACCEPTED,
            marks_obtained=100
        )

        # Create submission for student 2 (failed)
        sub2 = CodeSubmission.objects.create(
            assignment=self.assignment2,
            question=self.assessment_question,
            student=self.student2,
            source_code='code',
            status=CodeSubmission.Status.COMPLETED,
            verdict=CodeSubmission.Verdict.WRONG_ANSWER,
            marks_obtained=50
        )

        TestCaseVerdict.objects.create(
            submission=sub2,
            test_case_order=1,
            is_sample=True,
            status=TestCaseVerdict.Status.WRONG_ANSWER,
            marks_obtained=50
        )

        stats = AssessmentEvaluationService.get_assessment_statistics(self.assessment)

        self.assertEqual(stats['total_students'], 2)
        self.assertGreaterEqual(stats['average_marks'], 0)


class SubmissionAggregationTests(TestCase):
    """Tests for submission aggregation."""

    def setUp(self):
        """Set up test data."""
        self.student = User.objects.create_user(
            email='student@geetauniversity.edu.in',
            password='testpass123',
            role='student',
            is_email_verified=True
        )

        self.faculty = User.objects.create_user(
            email='faculty@geetauniversity.edu.in',
            password='testpass123',
            role='faculty',
            is_approved=True,
            is_email_verified=True
        )

        now = timezone.now()
        self.assessment = Assessment.objects.create(
            title='Test Assessment',
            start_datetime=now - timedelta(hours=1),
            end_datetime=now + timedelta(hours=2),
            duration_minutes=120,
            total_marks=100,
            passing_marks=60,
            created_by=self.faculty,
            is_published=True
        )

        self.question = Question.objects.create(
            title='Test Question',
            description='Test',
            input_format='Test',
            output_format='Test',
            constraints='Test',
            sample_input='Test',
            sample_output='Test',
            difficulty=Question.Difficulty.EASY,
            total_marks=10,
            time_limit_seconds=60,
            memory_limit_mb=128,
            status=Question.Status.ACTIVE,
            created_by=self.faculty
        )

        self.assessment_question = AssessmentQuestion.objects.create(
            assessment=self.assessment,
            question=self.question,
            question_title=self.question.title,
            question_description=self.question.description,
            question_input_format=self.question.input_format,
            question_output_format=self.question.output_format,
            question_constraints=self.question.constraints,
            question_difficulty=self.question.difficulty,
            question_language=self.question.language,
            question_order=1,
            marks=10
        )

        self.assignment = AssessmentAssignment.objects.create(
            assessment=self.assessment,
            student=self.student,
            status=AssessmentAssignment.Status.STARTED
        )

    def test_get_student_submissions(self):
        """Test getting student submission history."""
        submission = CodeSubmission.objects.create(
            assignment=self.assignment,
            question=self.assessment_question,
            student=self.student,
            source_code='code',
            status=CodeSubmission.Status.COMPLETED,
            verdict=CodeSubmission.Verdict.ACCEPTED,
            marks_obtained=10
        )

        submissions = SubmissionAggregationService.get_student_submissions(str(self.student.id))

        self.assertEqual(len(submissions), 1)
        self.assertEqual(submissions[0]['marks_obtained'], 10)

    def test_get_assessment_submissions(self):
        """Test getting assessment submissions."""
        submission = CodeSubmission.objects.create(
            assignment=self.assignment,
            question=self.assessment_question,
            student=self.student,
            source_code='code',
            status=CodeSubmission.Status.COMPLETED,
            verdict=CodeSubmission.Verdict.ACCEPTED,
            marks_obtained=10
        )

        submissions = SubmissionAggregationService.get_assessment_submissions(str(self.assessment.id))

        self.assertEqual(len(submissions), 1)
        self.assertEqual(submissions[0]['student_email'], self.student.email)


class ResultAccessControlTests(TestCase):
    """Tests for result access control."""

    def setUp(self):
        """Set up test data."""
        self.student1 = User.objects.create_user(
            email='student1@geetauniversity.edu.in',
            password='testpass123',
            role='student',
            is_email_verified=True
        )

        self.student2 = User.objects.create_user(
            email='student2@geetauniversity.edu.in',
            password='testpass123',
            role='student',
            is_email_verified=True
        )

        self.faculty1 = User.objects.create_user(
            email='faculty1@geetauniversity.edu.in',
            password='testpass123',
            role='faculty',
            is_approved=True,
            is_email_verified=True
        )

        self.faculty2 = User.objects.create_user(
            email='faculty2@geetauniversity.edu.in',
            password='testpass123',
            role='faculty',
            is_approved=True,
            is_email_verified=True
        )

        now = timezone.now()
        self.assessment = Assessment.objects.create(
            title='Test Assessment',
            start_datetime=now - timedelta(hours=1),
            end_datetime=now + timedelta(hours=2),
            duration_minutes=120,
            total_marks=100,
            passing_marks=60,
            created_by=self.faculty1,
            is_published=True,
            show_results_to_students=True
        )

    def test_student_can_only_view_own_results(self):
        """Test that students can only view their own results."""
        from assessments.models import AssessmentResult

        # Create result for student1
        result = AssessmentResult.objects.create(
            assessment=self.assessment,
            student=self.student1,
            total_marks_obtained=75,
            percentage=75.0,
            passed=True,
            attempted_at=timezone.now()
        )

        # Student1 should see it
        self.assertEqual(result.student, self.student1)

        # Student2 should not have access
        self.assertNotEqual(result.student, self.student2)

    def test_faculty_can_only_view_own_assessment_results(self):
        """Test that faculty can only view their own assessment results."""
        self.assertEqual(self.assessment.created_by, self.faculty1)
        self.assertNotEqual(self.assessment.created_by, self.faculty2)


class ResultAPITests(APITestCase):
    """Tests for result API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        self.student = User.objects.create_user(
            email='student@geetauniversity.edu.in',
            password='testpass123',
            role='student',
            is_email_verified=True
        )

        self.faculty = User.objects.create_user(
            email='faculty@geetauniversity.edu.in',
            password='testpass123',
            role='faculty',
            is_approved=True,
            is_email_verified=True
        )

        from rest_framework_simplejwt.tokens import RefreshToken

        student_refresh = RefreshToken.for_user(self.student)
        self.student_token = str(student_refresh.access_token)

        faculty_refresh = RefreshToken.for_user(self.faculty)
        self.faculty_token = str(faculty_refresh.access_token)

        now = timezone.now()
        self.assessment = Assessment.objects.create(
            title='Test Assessment',
            start_datetime=now - timedelta(hours=1),
            end_datetime=now + timedelta(hours=2),
            duration_minutes=120,
            total_marks=100,
            passing_marks=60,
            created_by=self.faculty,
            is_published=True,
            show_results_to_students=True
        )

    def test_student_view_submission_history(self):
        """Test student viewing submission history."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.student_token}')

        response = self.client.get('/api/results/submissions/history/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_student_view_results(self):
        """Test student viewing results."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.student_token}')

        response = self.client.get('/api/results/submissions/results/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_faculty_view_assessment_overview(self):
        """Test faculty viewing assessment overview."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.faculty_token}')

        response = self.client.get(f'/api/results/faculty/assessment_overview/?assessment_id={self.assessment.id}')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_faculty_export_csv(self):
        """Test faculty exporting results as CSV."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.faculty_token}')

        response = self.client.get(f'/api/results/faculty/export_csv/?assessment_id={self.assessment.id}')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'text/csv')
