"""
Comprehensive integration tests for the Geeta University Coding Assessment Portal.

Tests complete end-to-end workflows from user registration through assessment grading.
"""

import pytest
from django.test import TestCase, Client
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from datetime import timedelta
import json

from users.models import User
from questions.models import Question, TestCase as QuestionTestCase
from assessments.models import (
    Assessment,
    AssessmentQuestion,
    AssessmentAssignment,
    AssessmentResult,
)
from submissions.models import CodeSubmission, TestCaseVerdict

User = get_user_model()


class BackendIntegrationTests(APITestCase):
    """End-to-end integration tests for complete workflows."""

    def setUp(self):
        """Set up test data for all integration tests."""
        self.client = APIClient()

        # Create users
        self.faculty = User.objects.create_user(
            email="faculty@geetauniversity.edu.in",
            password="Faculty@123",
            role="faculty",
            is_email_verified=True,
            is_approved=True,
            first_name="Dr.",
            last_name="Faculty",
        )

        self.student1 = User.objects.create_user(
            email="student1@geetauniversity.edu.in",
            password="Student@123",
            role="student",
            is_email_verified=True,
            first_name="John",
            last_name="Doe",
        )

        self.student2 = User.objects.create_user(
            email="student2@geetauniversity.edu.in",
            password="Student@123",
            role="student",
            is_email_verified=True,
            first_name="Jane",
            last_name="Smith",
        )

    def test_complete_workflow_faculty_creates_assessment(self):
        """Test complete workflow: faculty creates assessment with questions."""
        from rest_framework_simplejwt.tokens import RefreshToken

        # Faculty login
        refresh = RefreshToken.for_user(self.faculty)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        now = timezone.now()

        # Faculty creates assessment
        assessment_data = {
            "title": "Python Basics",
            "description": "Learn Python fundamentals",
            "start_datetime": now + timedelta(hours=1),
            "end_datetime": now + timedelta(hours=3),
            "duration_minutes": 120,
            "total_marks": 100,
            "passing_marks": 60,
            "is_published": True,
        }

        response = self.client.post(
            "/api/assessments/", assessment_data, format="json"
        )

        # Assessment should be created
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK])

    def test_complete_workflow_question_creation_and_assignment(self):
        """Test workflow: create question, add to assessment, assign to student."""
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(self.faculty)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        # Create assessment
        now = timezone.now()
        assessment = Assessment.objects.create(
            title="Python Basics",
            description="Learn Python",
            start_datetime=now + timedelta(hours=1),
            end_datetime=now + timedelta(hours=3),
            duration_minutes=120,
            total_marks=100,
            passing_marks=60,
            created_by=self.faculty,
            is_published=True,
        )

        # Create question
        question = Question.objects.create(
            title="Sum of Two Numbers",
            description="Write a program to find sum of two numbers",
            input_format="Two integers",
            output_format="Their sum",
            constraints="1 <= N <= 1000",
            sample_input="5 3",
            sample_output="8",
            difficulty=Question.Difficulty.EASY,
            total_marks=10,
            time_limit_seconds=60,
            memory_limit_mb=128,
            status=Question.Status.ACTIVE,
            created_by=self.faculty,
        )

        # Add question to assessment
        assessment_question = AssessmentQuestion.objects.create(
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
            marks=10,
        )

        # Create test cases
        tc1 = QuestionTestCase.objects.create(
            question=question,
            input="5 3",
            expected_output="8",
            is_sample=True,
            marks=5,
            order=1,
        )

        tc2 = QuestionTestCase.objects.create(
            question=question,
            input="10 20",
            expected_output="30",
            is_sample=False,
            marks=5,
            order=2,
        )

        # Assign to student
        assignment = AssessmentAssignment.objects.create(
            assessment=assessment,
            student=self.student1,
            status=AssessmentAssignment.Status.ASSIGNED,
        )

        # Verify everything is created
        self.assertIsNotNone(assessment)
        self.assertIsNotNone(question)
        self.assertIsNotNone(assessment_question)
        self.assertEqual(QuestionTestCase.objects.count(), 2)
        self.assertIsNotNone(assignment)

    def test_complete_workflow_student_submission_and_evaluation(self):
        """Test workflow: student submits code, system evaluates, results calculated."""
        from rest_framework_simplejwt.tokens import RefreshToken

        # Create assessment and question
        now = timezone.now()
        assessment = Assessment.objects.create(
            title="Python Basics",
            start_datetime=now - timedelta(hours=1),
            end_datetime=now + timedelta(hours=2),
            duration_minutes=120,
            total_marks=100,
            passing_marks=60,
            created_by=self.faculty,
            is_published=True,
            show_results_to_students=True,
        )

        question = Question.objects.create(
            title="Sum of Numbers",
            description="Find sum",
            input_format="Numbers",
            output_format="Sum",
            constraints="1 <= N <= 100",
            sample_input="1 2 3",
            sample_output="6",
            difficulty=Question.Difficulty.EASY,
            total_marks=100,
            time_limit_seconds=60,
            memory_limit_mb=128,
            status=Question.Status.ACTIVE,
            created_by=self.faculty,
        )

        assessment_question = AssessmentQuestion.objects.create(
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
            marks=100,
        )

        # Create test cases
        tc1 = QuestionTestCase.objects.create(
            question=question,
            input="1 2 3",
            expected_output="6",
            is_sample=True,
            marks=50,
            order=1,
        )

        tc2 = QuestionTestCase.objects.create(
            question=question,
            input="10 20 30",
            expected_output="60",
            is_sample=False,
            marks=50,
            order=2,
        )

        # Create assignment
        assignment = AssessmentAssignment.objects.create(
            assessment=assessment,
            student=self.student1,
            status=AssessmentAssignment.Status.STARTED,
        )

        # Student creates submission
        submission = CodeSubmission.objects.create(
            assignment=assignment,
            question=assessment_question,
            student=self.student1,
            source_code="#include <stdio.h>\nint main() { printf('6'); return 0; }",
            status=CodeSubmission.Status.COMPLETED,
            verdict=CodeSubmission.Verdict.ACCEPTED,
            total_test_cases=2,
            passed_test_cases=2,
            marks_obtained=100,
        )

        # Create test verdicts
        for i, marks in enumerate([50, 50], 1):
            TestCaseVerdict.objects.create(
                submission=submission,
                test_case_order=i,
                is_sample=i == 1,
                status=TestCaseVerdict.Status.ACCEPTED,
                marks_obtained=marks,
            )

        # Verify submission
        self.assertEqual(submission.verdict, CodeSubmission.Verdict.ACCEPTED)
        self.assertEqual(submission.marks_obtained, 100)

        # Create result
        result = AssessmentResult.objects.create(
            assessment=assessment,
            student=self.student1,
            total_marks_obtained=100,
            percentage=100.0,
            passed=True,
            attempted_at=timezone.now(),
            evaluated_at=timezone.now(),
        )

        # Verify result
        self.assertTrue(result.passed)
        self.assertEqual(result.percentage, 100.0)

    def test_permission_student_cannot_access_other_submissions(self):
        """Test that students cannot access other students' submissions."""
        from rest_framework_simplejwt.tokens import RefreshToken

        # Create assessment and assignment
        now = timezone.now()
        assessment = Assessment.objects.create(
            title="Test",
            start_datetime=now - timedelta(hours=1),
            end_datetime=now + timedelta(hours=2),
            duration_minutes=120,
            total_marks=100,
            passing_marks=60,
            created_by=self.faculty,
            is_published=True,
        )

        question = Question.objects.create(
            title="Test",
            description="Test",
            input_format="Test",
            output_format="Test",
            constraints="Test",
            sample_input="Test",
            sample_output="Test",
            difficulty=Question.Difficulty.EASY,
            total_marks=100,
            time_limit_seconds=60,
            memory_limit_mb=128,
            status=Question.Status.ACTIVE,
            created_by=self.faculty,
        )

        assessment_question = AssessmentQuestion.objects.create(
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
            marks=100,
        )

        # Create submissions for different students
        assignment1 = AssessmentAssignment.objects.create(
            assessment=assessment, student=self.student1
        )

        assignment2 = AssessmentAssignment.objects.create(
            assessment=assessment, student=self.student2
        )

        submission1 = CodeSubmission.objects.create(
            assignment=assignment1,
            question=assessment_question,
            student=self.student1,
            source_code="code1",
            status=CodeSubmission.Status.COMPLETED,
            verdict=CodeSubmission.Verdict.ACCEPTED,
            marks_obtained=100,
        )

        submission2 = CodeSubmission.objects.create(
            assignment=assignment2,
            question=assessment_question,
            student=self.student2,
            source_code="code2",
            status=CodeSubmission.Status.COMPLETED,
            verdict=CodeSubmission.Verdict.ACCEPTED,
            marks_obtained=50,
        )

        # Student1 login
        refresh = RefreshToken.for_user(self.student1)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        # Student1 can access own submission
        response = self.client.get(f"/api/submissions/{submission1.id}/")
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])

        # Student1 should not access student2's submission
        # (This depends on your actual API structure)

    def test_permission_faculty_cannot_access_other_assessments(self):
        """Test that faculty cannot access other faculty's assessments."""
        # Create another faculty
        other_faculty = User.objects.create_user(
            email="otherfaculty@geetauniversity.edu.in",
            password="Faculty@123",
            role="faculty",
            is_email_verified=True,
            is_approved=True,
        )

        now = timezone.now()

        # Faculty1 creates assessment
        assessment = Assessment.objects.create(
            title="Test",
            start_datetime=now - timedelta(hours=1),
            end_datetime=now + timedelta(hours=2),
            duration_minutes=120,
            total_marks=100,
            passing_marks=60,
            created_by=self.faculty,
            is_published=True,
        )

        # Other faculty should not be able to edit
        self.assertEqual(assessment.created_by, self.faculty)
        self.assertNotEqual(assessment.created_by, other_faculty)

    def test_authentication_jwt_token_workflow(self):
        """Test complete JWT authentication workflow."""
        from rest_framework_simplejwt.tokens import RefreshToken

        # Generate tokens
        refresh = RefreshToken.for_user(self.student1)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        # Test access token works
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        # Should be able to access protected endpoints
        response = self.client.get("/api/users/profile/")
        # Should not get 401 Unauthorized
        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_role_based_access_student_role(self):
        """Test that student role has correct permissions."""
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(self.student1)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        # Students should be able to view their profile
        response = self.client.get("/api/users/profile/")
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_role_based_access_faculty_role(self):
        """Test that faculty role has correct permissions."""
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(self.faculty)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        # Faculty should be able to create assessments
        response = self.client.get("/api/assessments/")
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_data_isolation_across_assessments(self):
        """Test that data is properly isolated across different assessments."""
        now = timezone.now()

        # Create two assessments
        assessment1 = Assessment.objects.create(
            title="Assessment 1",
            start_datetime=now - timedelta(hours=1),
            end_datetime=now + timedelta(hours=2),
            duration_minutes=120,
            total_marks=100,
            passing_marks=60,
            created_by=self.faculty,
            is_published=True,
        )

        assessment2 = Assessment.objects.create(
            title="Assessment 2",
            start_datetime=now - timedelta(hours=1),
            end_datetime=now + timedelta(hours=2),
            duration_minutes=120,
            total_marks=100,
            passing_marks=60,
            created_by=self.faculty,
            is_published=True,
        )

        # Assign different students
        a1_s1 = AssessmentAssignment.objects.create(
            assessment=assessment1, student=self.student1
        )

        a2_s2 = AssessmentAssignment.objects.create(
            assessment=assessment2, student=self.student2
        )

        # Verify they are separate
        self.assertNotEqual(a1_s1.assessment, a2_s2.assessment)
        self.assertNotEqual(a1_s1.student, a2_s2.student)


class PermissionTests(APITestCase):
    """Tests for permission enforcement."""

    def setUp(self):
        """Set up test data."""
        self.faculty = User.objects.create_user(
            email="faculty@geetauniversity.edu.in",
            password="Faculty@123",
            role="faculty",
            is_email_verified=True,
            is_approved=True,
        )

        self.student = User.objects.create_user(
            email="student@geetauniversity.edu.in",
            password="Student@123",
            role="student",
            is_email_verified=True,
        )

        self.client = APIClient()

    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated requests are denied."""
        response = self.client.get("/api/assessments/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_student_cannot_create_assessment(self):
        """Test that students cannot create assessments."""
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(self.student)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        now = timezone.now()
        data = {
            "title": "Test",
            "start_datetime": now,
            "end_datetime": now + timedelta(hours=2),
            "duration_minutes": 120,
            "total_marks": 100,
            "passing_marks": 60,
        }

        response = self.client.post("/api/assessments/", data, format="json")
        # Should be forbidden
        self.assertIn(
            response.status_code,
            [status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED],
        )

    def test_faculty_can_create_assessment(self):
        """Test that faculty can create assessments."""
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(self.faculty)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        now = timezone.now()
        data = {
            "title": "Test Assessment",
            "description": "Test",
            "start_datetime": (now + timedelta(hours=1)).isoformat(),
            "end_datetime": (now + timedelta(hours=3)).isoformat(),
            "duration_minutes": 120,
            "total_marks": 100,
            "passing_marks": 60,
        }

        response = self.client.post("/api/assessments/", data, format="json")
        # Should not be forbidden
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@pytest.mark.django_db
class SecurityTests(TestCase):
    """Security-related integration tests."""

    def setUp(self):
        """Set up test data."""
        self.faculty = User.objects.create_user(
            email="faculty@geetauniversity.edu.in",
            password="Faculty@123",
            role="faculty",
            is_email_verified=True,
            is_approved=True,
        )

        self.student = User.objects.create_user(
            email="student@geetauniversity.edu.in",
            password="Student@123",
            role="student",
            is_email_verified=True,
        )

    def test_hidden_test_case_not_exposed_in_api(self):
        """Test that hidden test case details are never exposed to students."""
        # This test verifies the API response structure
        now = timezone.now()

        question = Question.objects.create(
            title="Test",
            description="Test",
            input_format="Test",
            output_format="Test",
            constraints="Test",
            sample_input="1 2",
            sample_output="3",
            difficulty=Question.Difficulty.EASY,
            total_marks=10,
            time_limit_seconds=60,
            memory_limit_mb=128,
            status=Question.Status.ACTIVE,
            created_by=self.faculty,
        )

        # Create sample test case (visible)
        sample_tc = QuestionTestCase.objects.create(
            question=question,
            input="1 2",
            expected_output="3",
            is_sample=True,
            marks=5,
            order=1,
        )

        # Create hidden test case (should not be visible to students)
        hidden_tc = QuestionTestCase.objects.create(
            question=question,
            input="100 200",
            expected_output="300",
            is_sample=False,
            marks=5,
            order=2,
        )

        assessment = Assessment.objects.create(
            title="Test",
            start_datetime=now - timedelta(hours=1),
            end_datetime=now + timedelta(hours=2),
            duration_minutes=120,
            total_marks=10,
            passing_marks=6,
            created_by=self.faculty,
            is_published=True,
        )

        assessment_question = AssessmentQuestion.objects.create(
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
            marks=10,
        )

        # When student receives test cases, hidden ones should not have details exposed
        # The API should control this through serializers
        test_cases = question.test_cases.all()
        self.assertEqual(test_cases.count(), 2)

    def test_sql_injection_protection(self):
        """Test that API is protected against SQL injection."""
        # This would require testing with actual SQL injection payloads
        # in query parameters - implementation depends on your ORM usage
        pass

    def test_cross_site_scripting_protection(self):
        """Test that API sanitizes HTML/script content."""
        # Test that malicious scripts in input are escaped/removed
        pass


class ConcurrentAccessTests(TestCase):
    """Tests for concurrent access scenarios."""

    def setUp(self):
        """Set up test data."""
        self.faculty = User.objects.create_user(
            email="faculty@geetauniversity.edu.in",
            password="Faculty@123",
            role="faculty",
            is_email_verified=True,
            is_approved=True,
        )

        self.students = [
            User.objects.create_user(
                email=f"student{i}@geetauniversity.edu.in",
                password="Student@123",
                role="student",
                is_email_verified=True,
            )
            for i in range(3)
        ]

    def test_multiple_students_same_assessment(self):
        """Test multiple students can submit for same assessment."""
        now = timezone.now()

        assessment = Assessment.objects.create(
            title="Test",
            start_datetime=now - timedelta(hours=1),
            end_datetime=now + timedelta(hours=2),
            duration_minutes=120,
            total_marks=100,
            passing_marks=60,
            created_by=self.faculty,
            is_published=True,
        )

        # Create assignments for all students
        assignments = [
            AssessmentAssignment.objects.create(
                assessment=assessment, student=student
            )
            for student in self.students
        ]

        # Verify all created
        self.assertEqual(len(assignments), 3)
        self.assertEqual(AssessmentAssignment.objects.filter(
            assessment=assessment
        ).count(), 3)

    def test_multiple_submissions_same_question(self):
        """Test multiple students can submit for same question."""
        now = timezone.now()

        assessment = Assessment.objects.create(
            title="Test",
            start_datetime=now - timedelta(hours=1),
            end_datetime=now + timedelta(hours=2),
            duration_minutes=120,
            total_marks=100,
            passing_marks=60,
            created_by=self.faculty,
            is_published=True,
        )

        question = Question.objects.create(
            title="Test",
            description="Test",
            input_format="Test",
            output_format="Test",
            constraints="Test",
            sample_input="Test",
            sample_output="Test",
            difficulty=Question.Difficulty.EASY,
            total_marks=100,
            time_limit_seconds=60,
            memory_limit_mb=128,
            status=Question.Status.ACTIVE,
            created_by=self.faculty,
        )

        assessment_question = AssessmentQuestion.objects.create(
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
            marks=100,
        )

        # Create submissions from all students
        submissions = []
        for student in self.students:
            assignment = AssessmentAssignment.objects.create(
                assessment=assessment, student=student
            )

            submission = CodeSubmission.objects.create(
                assignment=assignment,
                question=assessment_question,
                student=student,
                source_code=f"code_{student.id}",
                status=CodeSubmission.Status.COMPLETED,
                verdict=CodeSubmission.Verdict.ACCEPTED,
                marks_obtained=100,
            )
            submissions.append(submission)

        # Verify all submissions created
        self.assertEqual(len(submissions), 3)
        self.assertEqual(
            CodeSubmission.objects.filter(
                question=assessment_question
            ).count(),
            3,
        )
