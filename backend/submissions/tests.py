"""
Comprehensive tests for Code Submissions.

Tests models, services, execution, and API endpoints.
"""

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from datetime import timedelta
import uuid

from users.models import User
from questions.models import Question, TestCase as QuestionTestCase
from assessments.models import Assessment, AssessmentQuestion, AssessmentAssignment
from .models import CodeSubmission, TestCaseVerdict, ExecutionLog
from .services import SubmissionService, SubmissionSecurityService
from .execution_service import ComparisonService


class CodeSubmissionModelTests(TestCase):
    """Tests for CodeSubmission model."""

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
            input_format='N numbers',
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

    def test_submission_creation(self):
        """Test creating a submission."""
        submission = CodeSubmission.objects.create(
            assignment=self.assignment,
            question=self.assessment_question,
            student=self.student,
            source_code='#include <stdio.h>\nint main() { return 0; }',
            language='c'
        )

        self.assertEqual(submission.status, CodeSubmission.Status.PENDING)
        self.assertEqual(submission.verdict, CodeSubmission.Verdict.NOT_EVALUATED)
        self.assertEqual(submission.language, 'c')

    def test_submission_properties(self):
        """Test submission properties."""
        submission = CodeSubmission.objects.create(
            assignment=self.assignment,
            question=self.assessment_question,
            student=self.student,
            source_code='#include <stdio.h>\nint main() { return 0; }',
            language='c',
            total_test_cases=5,
            passed_test_cases=5,
            marks_obtained=10
        )

        self.assertTrue(submission.is_accepted)
        self.assertEqual(submission.get_success_rate(), 100.0)

    def test_submission_compilation_error(self):
        """Test submission with compilation error."""
        submission = CodeSubmission.objects.create(
            assignment=self.assignment,
            question=self.assessment_question,
            student=self.student,
            source_code='invalid c code',
            language='c',
            status=CodeSubmission.Status.COMPLETED,
            verdict=CodeSubmission.Verdict.COMPILATION_ERROR,
            compilation_error='Invalid syntax',
            marks_obtained=0
        )

        self.assertTrue(submission.is_compilation_error)


class TestCaseVerdictModelTests(TestCase):
    """Tests for TestCaseVerdict model."""

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

        self.submission = CodeSubmission.objects.create(
            assignment=self.assignment,
            question=self.assessment_question,
            student=self.student,
            source_code='#include <stdio.h>\nint main() { return 0; }',
            language='c'
        )

    def test_test_case_verdict_creation(self):
        """Test creating test case verdict."""
        verdict = TestCaseVerdict.objects.create(
            submission=self.submission,
            test_case_order=1,
            is_sample=True,
            status=TestCaseVerdict.Status.ACCEPTED,
            marks_obtained=10
        )

        self.assertEqual(verdict.status, TestCaseVerdict.Status.ACCEPTED)
        self.assertEqual(verdict.marks_obtained, 10)


class SubmissionSecurityTests(TestCase):
    """Tests for submission security validation."""

    def test_validate_empty_code(self):
        """Test validation of empty code."""
        is_valid, error = SubmissionSecurityService.validate_source_code('')
        self.assertFalse(is_valid)
        self.assertIn('empty', error.lower())

    def test_validate_code_without_includes(self):
        """Test validation of code without includes."""
        is_valid, error = SubmissionSecurityService.validate_source_code(
            'int main() { return 0; }'
        )
        self.assertFalse(is_valid)

    def test_validate_dangerous_patterns(self):
        """Test validation of dangerous patterns."""
        is_valid, error = SubmissionSecurityService.validate_source_code(
            '#include <stdio.h>\nint main() { system("rm -rf /"); }'
        )
        self.assertFalse(is_valid)
        self.assertIn('restricted', error.lower())

    def test_validate_valid_code(self):
        """Test validation of valid code."""
        is_valid, error = SubmissionSecurityService.validate_source_code(
            '#include <stdio.h>\nint main() { printf("Hello"); return 0; }'
        )
        self.assertTrue(is_valid)

    def test_code_statistics(self):
        """Test code statistics generation."""
        code = '#include <stdio.h>\n// Comment\nint main() { printf("Test"); }'
        stats = SubmissionSecurityService.get_code_statistics(code)

        self.assertEqual(stats['total_lines'], 3)
        self.assertEqual(stats['comment_lines'], 1)
        self.assertGreater(stats['char_count'], 0)


class ComparisonServiceTests(TestCase):
    """Tests for output comparison service."""

    def test_normalize_output_whitespace(self):
        """Test output normalization with whitespace."""
        output = "  hello  world  \n\n"
        normalized = ComparisonService.normalize_output(output)

        self.assertEqual(normalized, "hello world")

    def test_compare_outputs_exact_match(self):
        """Test exact output match."""
        actual = "hello\nworld"
        expected = "hello\nworld"

        self.assertTrue(ComparisonService.compare_outputs(actual, expected))

    def test_compare_outputs_whitespace_difference(self):
        """Test output match with whitespace differences."""
        actual = "hello  world"
        expected = "hello world"

        self.assertTrue(ComparisonService.compare_outputs(actual, expected))

    def test_compare_outputs_mismatch(self):
        """Test output mismatch."""
        actual = "hello"
        expected = "world"

        self.assertFalse(ComparisonService.compare_outputs(actual, expected))


class SubmissionServiceTests(TestCase):
    """Tests for submission service."""

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

    def test_validate_submission_eligibility(self):
        """Test submission eligibility validation."""
        is_eligible, error = SubmissionService.validate_submission_eligibility(
            student_id=str(self.student.id),
            assignment_id=str(self.assignment.id),
            question_id=str(self.assessment_question.id)
        )

        self.assertTrue(is_eligible)
        self.assertIsNone(error)

    def test_validate_submission_after_deadline(self):
        """Test eligibility after deadline."""
        past_assessment = Assessment.objects.create(
            title='Past Assessment',
            start_datetime=timezone.now() - timedelta(hours=3),
            end_datetime=timezone.now() - timedelta(hours=1),
            duration_minutes=120,
            total_marks=100,
            passing_marks=60,
            created_by=self.faculty,
            is_published=True
        )

        past_assignment = AssessmentAssignment.objects.create(
            assessment=past_assessment,
            student=self.student,
            status=AssessmentAssignment.Status.STARTED
        )

        is_eligible, error = SubmissionService.validate_submission_eligibility(
            student_id=str(self.student.id),
            assignment_id=str(past_assignment.id),
            question_id=str(self.assessment_question.id)
        )

        self.assertFalse(is_eligible)
        self.assertIn('Deadline', error)

    def test_create_submission(self):
        """Test creating submission."""
        submission, error = SubmissionService.create_submission(
            student_id=str(self.student.id),
            assignment_id=str(self.assignment.id),
            question_id=str(self.assessment_question.id),
            source_code='#include <stdio.h>\nint main() { return 0; }',
            ip_address='127.0.0.1'
        )

        self.assertIsNotNone(submission)
        self.assertIsNone(error)
        self.assertEqual(submission.student, self.student)
        self.assertEqual(submission.attempt_number, 1)


class SubmissionAPITests(APITestCase):
    """Tests for Submission API endpoints."""

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

        refresh = RefreshToken.for_user(self.student)
        self.student_token = str(refresh.access_token)

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

    def test_submit_code(self):
        """Test submitting code."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.student_token}')

        data = {
            'question_id': str(self.assessment_question.id),
            'source_code': '#include <stdio.h>\nint main() { printf("1"); return 0; }'
        }

        response = self.client.post(
            f'/api/submissions/submit/{self.assignment.id}/',
            data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('submission_id', response.data)

    def test_submit_invalid_code(self):
        """Test submitting invalid code."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.student_token}')

        data = {
            'question_id': str(self.assessment_question.id),
            'source_code': '#include <stdio.h>\nint main() { system("rm -rf /"); }'
        }

        response = self.client.post(
            f'/api/submissions/submit/{self.assignment.id}/',
            data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_submissions(self):
        """Test listing submissions."""
        # Create a submission
        CodeSubmission.objects.create(
            assignment=self.assignment,
            question=self.assessment_question,
            student=self.student,
            source_code='#include <stdio.h>\nint main() { return 0; }',
            language='c'
        )

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.student_token}')
        response = self.client.get('/api/submissions/list/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['results']), 0)
