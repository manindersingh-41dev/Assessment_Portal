"""
Comprehensive tests for Question Bank module.

Tests for question and test case creation, management, validation, and permissions.
"""

from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

from .models import Question, TestCase as TestCaseModel
from .services import QuestionService, TestCaseService

User = get_user_model()


class QuestionModelTests(TestCase):
    """Tests for Question model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='faculty@geetauniversity.edu.in',
            password='Pass123',
            role=User.ROLE_FACULTY,
            is_email_verified=True,
            is_faculty_approved=True
        )

    def test_create_question(self):
        """Test creating a question."""
        question = Question.objects.create(
            title='Sum of Numbers',
            description='Find sum of N numbers',
            input_format='First line: N',
            output_format='Sum of all numbers',
            constraints='1 <= N <= 1000',
            sample_input='3\n1 2 3',
            sample_output='6',
            difficulty=Question.Difficulty.EASY,
            topic='Basic Math',
            total_marks=10,
            time_limit_seconds=30,
            memory_limit_mb=128,
            created_by=self.user
        )

        self.assertEqual(question.title, 'Sum of Numbers')
        self.assertEqual(question.status, Question.Status.DRAFT)
        self.assertEqual(question.total_marks, 10)
        self.assertEqual(question.created_by, self.user)

    def test_question_defaults(self):
        """Test question default values."""
        question = Question.objects.create(
            title='Test Question',
            description='Test',
            input_format='Input',
            output_format='Output',
            constraints='Constraints',
            sample_input='Input',
            sample_output='Output',
            created_by=self.user
        )

        self.assertEqual(question.status, Question.Status.DRAFT)
        self.assertEqual(question.difficulty, Question.Difficulty.MEDIUM)
        self.assertEqual(question.language, Question.Language.C)
        self.assertEqual(question.total_marks, 10)
        self.assertEqual(question.time_limit_seconds, 30)
        self.assertEqual(question.memory_limit_mb, 128)


class TestCaseModelTests(TestCase):
    """Tests for TestCase model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='faculty@geetauniversity.edu.in',
            password='Pass123',
            role=User.ROLE_FACULTY,
            is_email_verified=True,
            is_faculty_approved=True
        )
        self.question = Question.objects.create(
            title='Test',
            description='Test',
            input_format='Input',
            output_format='Output',
            constraints='Constraints',
            sample_input='Input',
            sample_output='Output',
            total_marks=10,
            created_by=self.user
        )

    def test_create_test_case(self):
        """Test creating a test case."""
        tc = TestCaseModel.objects.create(
            question=self.question,
            input='3\n1 2 3',
            expected_output='6',
            is_sample=True,
            marks=5,
            order=1
        )

        self.assertEqual(tc.question, self.question)
        self.assertEqual(tc.marks, 5)
        self.assertTrue(tc.is_sample)

    def test_test_case_ordering(self):
        """Test test case ordering."""
        tc1 = TestCaseModel.objects.create(
            question=self.question,
            input='1',
            expected_output='1',
            marks=5,
            order=1
        )
        tc2 = TestCaseModel.objects.create(
            question=self.question,
            input='2',
            expected_output='2',
            marks=5,
            order=2
        )

        test_cases = list(self.question.test_cases.all())
        self.assertEqual(test_cases[0].order, 1)
        self.assertEqual(test_cases[1].order, 2)


class QuestionServiceTests(TestCase):
    """Tests for QuestionService."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='faculty@geetauniversity.edu.in',
            password='Pass123',
            role=User.ROLE_FACULTY,
            is_email_verified=True,
            is_faculty_approved=True
        )
        self.question = Question.objects.create(
            title='Test',
            description='Test',
            input_format='Input',
            output_format='Output',
            constraints='Constraints',
            sample_input='Input',
            sample_output='Output',
            total_marks=10,
            created_by=self.user
        )

    def test_validate_test_case_marks(self):
        """Test validating test case marks."""
        # No test cases
        is_valid, message, marks = QuestionService.validate_test_case_marks(self.question)
        self.assertFalse(is_valid)

        # Add test cases with correct marks
        TestCaseModel.objects.create(
            question=self.question,
            input='1',
            expected_output='1',
            marks=5,
            order=1
        )
        TestCaseModel.objects.create(
            question=self.question,
            input='2',
            expected_output='2',
            marks=5,
            order=2
        )

        is_valid, message, marks = QuestionService.validate_test_case_marks(self.question)
        self.assertTrue(is_valid)
        self.assertEqual(marks, 10)

    def test_validate_sample_test_cases(self):
        """Test validating sample test cases."""
        # No sample test cases
        is_valid, message = QuestionService.validate_sample_test_cases(self.question)
        self.assertFalse(is_valid)

        # Add sample test case
        TestCaseModel.objects.create(
            question=self.question,
            input='1',
            expected_output='1',
            is_sample=True,
            marks=10,
            order=1
        )

        is_valid, message = QuestionService.validate_sample_test_cases(self.question)
        self.assertTrue(is_valid)

    def test_can_publish(self):
        """Test checking if question can be published."""
        # No test cases
        can_publish, message = QuestionService.can_publish(self.question)
        self.assertFalse(can_publish)

        # Add test cases
        TestCaseModel.objects.create(
            question=self.question,
            input='1',
            expected_output='1',
            is_sample=True,
            marks=10,
            order=1
        )

        # Now it should be publishable
        can_publish, message = QuestionService.can_publish(self.question)
        self.assertTrue(can_publish)


class TestCaseServiceTests(TestCase):
    """Tests for TestCaseService."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='faculty@geetauniversity.edu.in',
            password='Pass123',
            role=User.ROLE_FACULTY,
            is_email_verified=True,
            is_faculty_approved=True
        )
        self.question = Question.objects.create(
            title='Test',
            description='Test',
            input_format='Input',
            output_format='Output',
            constraints='Constraints',
            sample_input='Input',
            sample_output='Output',
            total_marks=10,
            created_by=self.user
        )

    def test_create_test_cases(self):
        """Test creating multiple test cases."""
        test_cases_data = [
            {'input': '1', 'expected_output': '1', 'is_sample': True, 'marks': 5},
            {'input': '2', 'expected_output': '2', 'is_sample': False, 'marks': 5},
        ]

        success, message, count = TestCaseService.create_test_cases(
            self.question, test_cases_data
        )

        self.assertTrue(success)
        self.assertEqual(count, 2)
        self.assertEqual(self.question.test_cases.count(), 2)

    def test_create_test_cases_invalid_marks(self):
        """Test creating test cases with invalid total marks."""
        test_cases_data = [
            {'input': '1', 'expected_output': '1', 'marks': 8},
            {'input': '2', 'expected_output': '2', 'marks': 5},
        ]

        success, message, count = TestCaseService.create_test_cases(
            self.question, test_cases_data
        )

        self.assertFalse(success)
        self.assertEqual(count, 0)


class QuestionAPITests(APITestCase):
    """Tests for Question API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        self.faculty = User.objects.create_user(
            email='faculty@geetauniversity.edu.in',
            password='Pass123',
            role=User.ROLE_FACULTY,
            is_email_verified=True,
            is_faculty_approved=True
        )

        self.student = User.objects.create_user(
            email='student@geetauniversity.edu.in',
            password='Pass123',
            role=User.ROLE_STUDENT,
            is_email_verified=True
        )

        self.client.force_authenticate(user=self.faculty)

    def test_create_question(self):
        """Test creating a question via API."""
        data = {
            'title': 'Sum of Numbers',
            'description': 'Find sum of N numbers',
            'input_format': 'First line: N',
            'output_format': 'Sum',
            'constraints': 'Constraints',
            'sample_input': '3\n1 2 3',
            'sample_output': '6',
            'difficulty': 'easy',
            'topic': 'Math',
            'total_marks': 10,
            'time_limit_seconds': 30,
            'memory_limit_mb': 128,
            'test_cases': [
                {
                    'input': '3\n1 2 3',
                    'expected_output': '6',
                    'is_sample': True,
                    'marks': 5,
                    'order': 1
                },
                {
                    'input': '5\n1 2 3 4 5',
                    'expected_output': '15',
                    'is_sample': False,
                    'marks': 5,
                    'order': 2
                }
            ]
        }

        response = self.client.post('/api/questions/questions/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Question.objects.count(), 1)

    def test_create_question_invalid_marks(self):
        """Test creating question with invalid test case marks."""
        data = {
            'title': 'Test',
            'description': 'Test',
            'input_format': 'Input',
            'output_format': 'Output',
            'constraints': 'Constraints',
            'sample_input': 'Input',
            'sample_output': 'Output',
            'total_marks': 10,
            'test_cases': [
                {
                    'input': '1',
                    'expected_output': '1',
                    'is_sample': True,
                    'marks': 8,
                    'order': 1
                }
            ]
        }

        response = self.client.post('/api/questions/questions/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_publish_question(self):
        """Test publishing a question."""
        question = Question.objects.create(
            title='Test',
            description='Test',
            input_format='Input',
            output_format='Output',
            constraints='Constraints',
            sample_input='Input',
            sample_output='Output',
            total_marks=10,
            created_by=self.faculty
        )

        # Add test case
        TestCaseModel.objects.create(
            question=question,
            input='1',
            expected_output='1',
            is_sample=True,
            marks=10,
            order=1
        )

        response = self.client.post(
            f'/api/questions/questions/{question.id}/publish/'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        question.refresh_from_db()
        self.assertEqual(question.status, Question.Status.ACTIVE)

    def test_archive_question(self):
        """Test archiving a question."""
        question = Question.objects.create(
            title='Test',
            description='Test',
            input_format='Input',
            output_format='Output',
            constraints='Constraints',
            sample_input='Input',
            sample_output='Output',
            status=Question.Status.ACTIVE,
            created_by=self.faculty
        )

        response = self.client.post(
            f'/api/questions/questions/{question.id}/archive/'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        question.refresh_from_db()
        self.assertEqual(question.status, Question.Status.ARCHIVED)

    def test_delete_draft_question(self):
        """Test deleting a draft question."""
        question = Question.objects.create(
            title='Test',
            description='Test',
            input_format='Input',
            output_format='Output',
            constraints='Constraints',
            sample_input='Input',
            sample_output='Output',
            status=Question.Status.DRAFT,
            created_by=self.faculty
        )

        response = self.client.delete(
            f'/api/questions/questions/{question.id}/'
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Question.objects.filter(id=question.id).exists())

    def test_cannot_delete_active_question(self):
        """Test that active questions cannot be deleted."""
        question = Question.objects.create(
            title='Test',
            description='Test',
            input_format='Input',
            output_format='Output',
            constraints='Constraints',
            sample_input='Input',
            sample_output='Output',
            status=Question.Status.ACTIVE,
            created_by=self.faculty
        )

        response = self.client.delete(
            f'/api/questions/questions/{question.id}/'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Question.objects.filter(id=question.id).exists())

    def test_list_questions_only_faculty_own(self):
        """Test that faculty can only see their own questions."""
        question1 = Question.objects.create(
            title='Question 1',
            description='Test',
            input_format='Input',
            output_format='Output',
            constraints='Constraints',
            sample_input='Input',
            sample_output='Output',
            created_by=self.faculty
        )

        # Create another faculty
        other_faculty = User.objects.create_user(
            email='other@geetauniversity.edu.in',
            password='Pass123',
            role=User.ROLE_FACULTY,
            is_email_verified=True,
            is_faculty_approved=True
        )

        question2 = Question.objects.create(
            title='Question 2',
            description='Test',
            input_format='Input',
            output_format='Output',
            constraints='Constraints',
            sample_input='Input',
            sample_output='Output',
            created_by=other_faculty
        )

        response = self.client.get('/api/questions/questions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_student_cannot_create_question(self):
        """Test that students cannot create questions."""
        self.client.force_authenticate(user=self.student)

        data = {
            'title': 'Test',
            'description': 'Test',
            'input_format': 'Input',
            'output_format': 'Output',
            'constraints': 'Constraints',
            'sample_input': 'Input',
            'sample_output': 'Output',
            'total_marks': 10
        }

        response = self.client.post('/api/questions/questions/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TestCaseAPITests(APITestCase):
    """Tests for TestCase API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        self.faculty = User.objects.create_user(
            email='faculty@geetauniversity.edu.in',
            password='Pass123',
            role=User.ROLE_FACULTY,
            is_email_verified=True,
            is_faculty_approved=True
        )

        self.question = Question.objects.create(
            title='Test',
            description='Test',
            input_format='Input',
            output_format='Output',
            constraints='Constraints',
            sample_input='Input',
            sample_output='Output',
            total_marks=10,
            created_by=self.faculty
        )

        self.client.force_authenticate(user=self.faculty)

    def test_create_test_case(self):
        """Test creating a test case via API."""
        data = {
            'question_id': str(self.question.id),
            'input': '1',
            'expected_output': '1',
            'is_sample': True,
            'marks': 10,
            'order': 1
        }

        response = self.client.post('/api/questions/test-cases/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_cannot_exceed_question_marks(self):
        """Test that test cases cannot exceed question total marks."""
        # Add a test case first
        TestCaseModel.objects.create(
            question=self.question,
            input='1',
            expected_output='1',
            marks=8,
            order=1
        )

        data = {
            'question_id': str(self.question.id),
            'input': '2',
            'expected_output': '2',
            'is_sample': True,
            'marks': 5,
            'order': 2
        }

        response = self.client.post('/api/questions/test-cases/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_test_case(self):
        """Test deleting a test case."""
        tc = TestCaseModel.objects.create(
            question=self.question,
            input='1',
            expected_output='1',
            marks=10,
            order=1
        )

        # Add another test case so we can delete this one
        TestCaseModel.objects.create(
            question=self.question,
            input='2',
            expected_output='2',
            marks=0,  # This is for illustration; ideally wouldn't be 0
            order=2
        )

        response = self.client.delete(
            f'/api/questions/test-cases/{tc.id}/'
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
