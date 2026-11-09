"""
Comprehensive tests for Assessment Management.

Tests models, serializers, services, and API endpoints.
"""

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from datetime import timedelta

from users.models import User
from questions.models import Question, TestCase as QuestionTestCase
from .models import (
    Assessment, AssessmentQuestion, StudentBatch,
    AssessmentAssignment, AssessmentResult
)
from .services import AssessmentService, AssignmentService


class AssessmentModelTests(TestCase):
    """Tests for Assessment model."""

    def setUp(self):
        """Set up test data."""
        self.faculty = User.objects.create_user(
            email='faculty@geetauniversity.edu.in',
            password='testpass123',
            first_name='John',
            last_name='Doe',
            role='faculty',
            is_approved=True,
            is_email_verified=True
        )

        self.now = timezone.now()
        self.start_time = self.now + timedelta(hours=1)
        self.end_time = self.start_time + timedelta(hours=2)

    def test_assessment_creation(self):
        """Test creating assessment."""
        assessment = Assessment.objects.create(
            title='Python Basics',
            description='Test your Python skills',
            start_datetime=self.start_time,
            end_datetime=self.end_time,
            duration_minutes=120,
            total_marks=100,
            passing_marks=60,
            created_by=self.faculty
        )

        self.assertEqual(assessment.title, 'Python Basics')
        self.assertEqual(assessment.status, Assessment.Status.DRAFT)
        self.assertFalse(assessment.is_published)

    def test_assessment_timing_properties(self):
        """Test assessment timing properties."""
        assessment = Assessment.objects.create(
            title='Test Assessment',
            start_datetime=self.start_time,
            end_datetime=self.end_time,
            duration_minutes=120,
            total_marks=100,
            passing_marks=60,
            created_by=self.faculty
        )

        self.assertFalse(assessment.is_active_now)
        self.assertFalse(assessment.is_started)
        self.assertFalse(assessment.is_ended)

    def test_assessment_question_count(self):
        """Test question count property."""
        assessment = Assessment.objects.create(
            title='Test Assessment',
            start_datetime=self.start_time,
            end_datetime=self.end_time,
            duration_minutes=120,
            total_marks=100,
            passing_marks=60,
            created_by=self.faculty
        )

        self.assertEqual(assessment.question_count, 0)


class AssessmentQuestionModelTests(TestCase):
    """Tests for AssessmentQuestion model."""

    def setUp(self):
        """Set up test data."""
        self.faculty = User.objects.create_user(
            email='faculty@geetauniversity.edu.in',
            password='testpass123',
            role='faculty',
            is_approved=True,
            is_email_verified=True
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

        now = timezone.now()
        self.assessment = Assessment.objects.create(
            title='Test',
            start_datetime=now + timedelta(hours=1),
            end_datetime=now + timedelta(hours=3),
            duration_minutes=120,
            total_marks=10,
            passing_marks=6,
            created_by=self.faculty
        )

    def test_assessment_question_creation(self):
        """Test creating assessment question."""
        aq = AssessmentQuestion.objects.create(
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

        self.assertEqual(aq.marks, 10)
        self.assertTrue(aq.is_mandatory)
        self.assertTrue(aq.show_to_students)


class AssessmentAssignmentModelTests(TestCase):
    """Tests for AssessmentAssignment model."""

    def setUp(self):
        """Set up test data."""
        self.faculty = User.objects.create_user(
            email='faculty@geetauniversity.edu.in',
            password='testpass123',
            role='faculty',
            is_approved=True,
            is_email_verified=True
        )

        self.student = User.objects.create_user(
            email='student@geetauniversity.edu.in',
            password='testpass123',
            role='student',
            is_email_verified=True
        )

        now = timezone.now()
        self.assessment = Assessment.objects.create(
            title='Test',
            start_datetime=now + timedelta(hours=1),
            end_datetime=now + timedelta(hours=3),
            duration_minutes=120,
            total_marks=100,
            passing_marks=60,
            created_by=self.faculty,
            is_published=True
        )

    def test_assignment_creation(self):
        """Test creating assignment."""
        assignment = AssessmentAssignment.objects.create(
            assessment=self.assessment,
            student=self.student
        )

        self.assertEqual(assignment.status, AssessmentAssignment.Status.ASSIGNED)
        self.assertEqual(assignment.attempt_number, 1)
        self.assertIsNone(assignment.marks_obtained)

    def test_assignment_can_start_timing_check(self):
        """Test can_start respects timing."""
        assignment = AssessmentAssignment.objects.create(
            assessment=self.assessment,
            student=self.student
        )

        # Cannot start before assessment starts
        self.assertFalse(assignment.can_start())

    def test_assignment_mark_started(self):
        """Test marking assignment as started."""
        assignment = AssessmentAssignment.objects.create(
            assessment=self.assessment,
            student=self.student
        )

        assignment.mark_started()

        self.assertEqual(assignment.status, AssessmentAssignment.Status.STARTED)
        self.assertIsNotNone(assignment.started_at)

    def test_assignment_mark_submitted(self):
        """Test marking assignment as submitted."""
        assignment = AssessmentAssignment.objects.create(
            assessment=self.assessment,
            student=self.student,
            status=AssessmentAssignment.Status.STARTED
        )

        assignment.mark_submitted()

        self.assertEqual(assignment.status, AssessmentAssignment.Status.SUBMITTED)
        self.assertIsNotNone(assignment.submitted_at)


class StudentBatchModelTests(TestCase):
    """Tests for StudentBatch model."""

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

    def test_batch_creation(self):
        """Test creating batch."""
        batch = StudentBatch.objects.create(
            name='CSE 2024',
            department='Computer Science',
            year=2
        )

        self.assertEqual(batch.name, 'CSE 2024')
        self.assertEqual(batch.year, 2)

    def test_batch_add_students(self):
        """Test adding students to batch."""
        batch = StudentBatch.objects.create(
            name='CSE 2024',
            department='Computer Science',
            year=2
        )

        batch.students.add(self.student1, self.student2)

        self.assertEqual(batch.students.count(), 2)


class AssessmentServiceTests(TestCase):
    """Tests for AssessmentService."""

    def setUp(self):
        """Set up test data."""
        self.faculty = User.objects.create_user(
            email='faculty@geetauniversity.edu.in',
            password='testpass123',
            role='faculty',
            is_approved=True,
            is_email_verified=True
        )

        now = timezone.now()
        self.start_time = now + timedelta(hours=1)
        self.end_time = self.start_time + timedelta(hours=2)

    def test_validate_assessment_timing(self):
        """Test assessment timing validation."""
        # Valid timing
        errors = AssessmentService.validate_assessment_timing(
            self.start_time,
            self.end_time,
            120
        )
        self.assertEqual(len(errors), 0)

        # Invalid: start after end
        errors = AssessmentService.validate_assessment_timing(
            self.end_time,
            self.start_time,
            120
        )
        self.assertGreater(len(errors), 0)

    def test_validate_marks_configuration(self):
        """Test marks validation."""
        # Valid
        errors = AssessmentService.validate_marks_configuration(100, 60, 100)
        self.assertEqual(len(errors), 0)

        # Passing > total
        errors = AssessmentService.validate_marks_configuration(100, 120, 100)
        self.assertGreater(len(errors), 0)

        # Question marks mismatch
        errors = AssessmentService.validate_marks_configuration(100, 60, 80)
        self.assertGreater(len(errors), 0)


class AssignmentServiceTests(TestCase):
    """Tests for AssignmentService."""

    def setUp(self):
        """Set up test data."""
        self.faculty = User.objects.create_user(
            email='faculty@geetauniversity.edu.in',
            password='testpass123',
            role='faculty',
            is_approved=True,
            is_email_verified=True
        )

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

        now = timezone.now()
        self.assessment = Assessment.objects.create(
            title='Test',
            start_datetime=now + timedelta(hours=1),
            end_datetime=now + timedelta(hours=3),
            duration_minutes=120,
            total_marks=100,
            passing_marks=60,
            created_by=self.faculty,
            is_published=True
        )

    def test_create_assignments_individual(self):
        """Test creating assignments for individual students."""
        assignments = AssignmentService.create_assignments(
            self.assessment,
            student_ids=[str(self.student1.id), str(self.student2.id)]
        )

        self.assertEqual(len(assignments), 2)
        self.assertTrue(
            AssessmentAssignment.objects.filter(
                assessment=self.assessment,
                student=self.student1
            ).exists()
        )

    def test_create_assignments_batch(self):
        """Test creating assignments for batch."""
        batch = StudentBatch.objects.create(
            name='Test Batch',
            year=2
        )
        batch.students.add(self.student1, self.student2)

        assignments = AssignmentService.create_assignments(
            self.assessment,
            batch_ids=[str(batch.id)]
        )

        self.assertEqual(len(assignments), 2)

    def test_evaluate_assignment(self):
        """Test evaluating assignment."""
        assignment = AssessmentAssignment.objects.create(
            assessment=self.assessment,
            student=self.student1,
            status=AssessmentAssignment.Status.SUBMITTED,
            submitted_at=timezone.now()
        )

        AssignmentService.evaluate_assignment(
            assignment,
            marks_obtained=75,
            feedback='Good job'
        )

        assignment.refresh_from_db()
        self.assertEqual(assignment.marks_obtained, 75)
        self.assertTrue(assignment.passed)
        self.assertEqual(assignment.status, AssessmentAssignment.Status.GRADED)

        # Check result was created
        result = AssessmentResult.objects.get(
            assessment=self.assessment,
            student=self.student1
        )
        self.assertEqual(result.total_marks_obtained, 75)
        self.assertTrue(result.passed)


class AssessmentAPITests(APITestCase):
    """Tests for Assessment API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        self.faculty = User.objects.create_user(
            email='faculty@geetauniversity.edu.in',
            password='testpass123',
            first_name='John',
            last_name='Doe',
            role='faculty',
            is_approved=True,
            is_email_verified=True
        )

        self.student = User.objects.create_user(
            email='student@geetauniversity.edu.in',
            password='testpass123',
            role='student',
            is_email_verified=True
        )

        # Get JWT token for faculty
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(self.faculty)
        self.faculty_token = str(refresh.access_token)

        refresh = RefreshToken.for_user(self.student)
        self.student_token = str(refresh.access_token)

        now = timezone.now()
        self.start_time = now + timedelta(hours=1)
        self.end_time = self.start_time + timedelta(hours=2)

    def test_create_assessment(self):
        """Test creating assessment via API."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.faculty_token}')

        data = {
            'title': 'Python Basics',
            'description': 'Test Python skills',
            'start_datetime': self.start_time.isoformat(),
            'end_datetime': self.end_time.isoformat(),
            'duration_minutes': 120,
            'total_marks': 100,
            'passing_marks': 60
        }

        response = self.client.post('/api/assessments/assessments/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue('assessment' in response.data)

    def test_list_assessments_faculty(self):
        """Test listing assessments as faculty."""
        Assessment.objects.create(
            title='Test Assessment',
            start_datetime=self.start_time,
            end_datetime=self.end_time,
            duration_minutes=120,
            total_marks=100,
            passing_marks=60,
            created_by=self.faculty
        )

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.faculty_token}')
        response = self.client.get('/api/assessments/assessments/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_list_assessments_student(self):
        """Test listing assessments as student."""
        assessment = Assessment.objects.create(
            title='Test Assessment',
            start_datetime=self.start_time,
            end_datetime=self.end_time,
            duration_minutes=120,
            total_marks=100,
            passing_marks=60,
            created_by=self.faculty,
            is_published=True
        )

        AssessmentAssignment.objects.create(
            assessment=assessment,
            student=self.student
        )

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.student_token}')
        response = self.client.get('/api/assessments/assessments/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_publish_assessment(self):
        """Test publishing assessment."""
        assessment = Assessment.objects.create(
            title='Test Assessment',
            start_datetime=self.start_time,
            end_datetime=self.end_time,
            duration_minutes=120,
            total_marks=100,
            passing_marks=60,
            created_by=self.faculty
        )

        question = Question.objects.create(
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

        AssessmentQuestion.objects.create(
            assessment=assessment,
            question=question,
            question_title=question.title,
            question_description=question.description,
            question_input_format=question.input_format,
            question_output_format=question.output_format,
            question_constraints=question.constraints,
            question_difficulty=question.difficulty,
            question_language=question.language,
            question_order=1,
            marks=100
        )

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.faculty_token}')
        response = self.client.post(f'/api/assessments/assessments/{assessment.id}/publish/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assessment.refresh_from_db()
        self.assertTrue(assessment.is_published)

    def test_assign_assessment(self):
        """Test assigning assessment to students."""
        assessment = Assessment.objects.create(
            title='Test Assessment',
            start_datetime=self.start_time,
            end_datetime=self.end_time,
            duration_minutes=120,
            total_marks=100,
            passing_marks=60,
            created_by=self.faculty,
            is_published=True
        )

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.faculty_token}')

        data = {
            'student_ids': [str(self.student.id)]
        }

        response = self.client.post(
            f'/api/assessments/assessments/{assessment.id}/assign/',
            data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            AssessmentAssignment.objects.filter(
                assessment=assessment,
                student=self.student
            ).exists()
        )


class AssessmentAssignmentAPITests(APITestCase):
    """Tests for AssessmentAssignment API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        self.faculty = User.objects.create_user(
            email='faculty@geetauniversity.edu.in',
            password='testpass123',
            role='faculty',
            is_approved=True,
            is_email_verified=True
        )

        self.student = User.objects.create_user(
            email='student@geetauniversity.edu.in',
            password='testpass123',
            role='student',
            is_email_verified=True
        )

        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(self.faculty)
        self.faculty_token = str(refresh.access_token)

        refresh = RefreshToken.for_user(self.student)
        self.student_token = str(refresh.access_token)

        now = timezone.now()
        self.assessment = Assessment.objects.create(
            title='Test Assessment',
            start_datetime=now + timedelta(hours=1),
            end_datetime=now + timedelta(hours=3),
            duration_minutes=120,
            total_marks=100,
            passing_marks=60,
            created_by=self.faculty,
            is_published=True
        )

        self.assignment = AssessmentAssignment.objects.create(
            assessment=self.assessment,
            student=self.student
        )

    def test_list_assignments_student(self):
        """Test student viewing their assignments."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.student_token}')
        response = self.client.get('/api/assessments/assignments/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_list_assignments_faculty(self):
        """Test faculty viewing assessment assignments."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.faculty_token}')
        response = self.client.get('/api/assessments/assignments/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
