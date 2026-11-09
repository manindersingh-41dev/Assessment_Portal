"""
Tests for authentication and user management.

Comprehensive tests for registration, email verification, login,
password reset, and profile management.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from datetime import timedelta

from .models import User, StudentProfile, FacultyProfile, EmailOTP, LoginAttempt
from .services import AuthenticationService, UserService


class UserModelTests(TestCase):
    """Tests for User model."""

    def test_create_user(self):
        """Test creating a regular user."""
        user = User.objects.create_user(
            email='student@geetauniversity.edu.in',
            password='TestPass123',
            role=User.ROLE_STUDENT
        )
        self.assertEqual(user.email, 'student@geetauniversity.edu.in')
        self.assertTrue(user.check_password('TestPass123'))
        self.assertFalse(user.is_email_verified)

    def test_create_superuser(self):
        """Test creating a superuser."""
        admin = User.objects.create_superuser(
            email='admin@geetauniversity.edu.in',
            password='AdminPass123'
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_email_verified)

    def test_invalid_email_domain(self):
        """Test that non-university emails are rejected."""
        with self.assertRaises(Exception):
            User.objects.create_user(
                email='user@gmail.com',
                password='TestPass123'
            )

    def test_user_is_student(self):
        """Test is_student() method."""
        student = User.objects.create_user(
            email='student@geetauniversity.edu.in',
            password='Pass123',
            role=User.ROLE_STUDENT
        )
        self.assertTrue(student.is_student())
        self.assertFalse(student.is_faculty())

    def test_user_is_faculty(self):
        """Test is_faculty() method."""
        faculty = User.objects.create_user(
            email='faculty@geetauniversity.edu.in',
            password='Pass123',
            role=User.ROLE_FACULTY
        )
        self.assertTrue(faculty.is_faculty())
        self.assertFalse(faculty.is_student())

    def test_can_use_system(self):
        """Test can_use_system() method."""
        user = User.objects.create_user(
            email='user@geetauniversity.edu.in',
            password='Pass123'
        )
        self.assertFalse(user.can_use_system())  # Email not verified

        user.is_email_verified = True
        self.assertTrue(user.can_use_system())

        user.is_active = False
        self.assertFalse(user.can_use_system())


class StudentProfileTests(TestCase):
    """Tests for StudentProfile model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='student@geetauniversity.edu.in',
            password='Pass123',
            role=User.ROLE_STUDENT
        )

    def test_create_student_profile(self):
        """Test creating a student profile."""
        profile = StudentProfile.objects.create(
            user=self.user,
            roll_number='2024001',
            department='Computer Science',
            year_of_study=1
        )
        self.assertEqual(profile.roll_number, '2024001')
        self.assertEqual(profile.department, 'Computer Science')

    def test_unique_roll_number(self):
        """Test that roll numbers are unique."""
        StudentProfile.objects.create(
            user=self.user,
            roll_number='2024001',
            department='Computer Science'
        )

        user2 = User.objects.create_user(
            email='student2@geetauniversity.edu.in',
            password='Pass123',
            role=User.ROLE_STUDENT
        )

        with self.assertRaises(Exception):
            StudentProfile.objects.create(
                user=user2,
                roll_number='2024001',  # Duplicate
                department='Computer Science'
            )


class EmailOTPTests(TestCase):
    """Tests for EmailOTP model."""

    def test_create_otp(self):
        """Test creating an OTP."""
        otp = EmailOTP.create_otp('user@geetauniversity.edu.in')
        self.assertEqual(len(otp.otp), 6)
        self.assertTrue(otp.otp.isdigit())
        self.assertFalse(otp.is_used)

    def test_otp_expiry(self):
        """Test OTP expiry."""
        otp = EmailOTP.create_otp('user@geetauniversity.edu.in', expires_in_minutes=0)
        otp.expires_at = timezone.now() - timedelta(minutes=1)
        otp.save()
        self.assertTrue(otp.is_expired)

    def test_mark_otp_used(self):
        """Test marking OTP as used."""
        otp = EmailOTP.create_otp('user@geetauniversity.edu.in')
        otp.mark_used()
        self.assertTrue(otp.is_used)
        self.assertIsNotNone(otp.used_at)


class AuthenticationServiceTests(TestCase):
    """Tests for AuthenticationService."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='user@geetauniversity.edu.in',
            password='Pass123'
        )

    def test_verify_email(self):
        """Test email verification with OTP."""
        otp = EmailOTP.create_otp(self.user.email)

        success, user, message = AuthenticationService.verify_email(
            self.user.email,
            otp.otp
        )

        self.assertTrue(success)
        self.assertEqual(user.id, self.user.id)
        self.assertTrue(otp.is_used)

    def test_reset_password(self):
        """Test password reset."""
        otp = EmailOTP.create_otp(
            self.user.email,
            purpose='password_reset'
        )
        new_password = 'NewPass123'

        success, user, message = AuthenticationService.reset_password(
            self.user.email,
            otp.otp,
            new_password
        )

        self.assertTrue(success)
        user.refresh_from_db()
        self.assertTrue(user.check_password(new_password))

    def test_brute_force_protection(self):
        """Test brute-force protection."""
        for _ in range(5):
            AuthenticationService.record_login_attempt(
                self.user.email,
                '127.0.0.1',
                success=False
            )

        self.assertTrue(AuthenticationService.is_login_blocked(self.user.email))


class RegistrationAPITests(APITestCase):
    """Tests for registration APIs."""

    def test_student_registration(self):
        """Test student registration."""
        data = {
            'email': 'student@geetauniversity.edu.in',
            'password': 'SecurePass123',
            'password_confirm': 'SecurePass123',
            'roll_number': '2024001',
            'department': 'Computer Science',
            'year_of_study': 1,
        }

        response = self.client.post('/api/auth/register/student/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email=data['email']).exists())

    def test_student_registration_invalid_email_domain(self):
        """Test that non-university emails are rejected."""
        data = {
            'email': 'student@gmail.com',
            'password': 'SecurePass123',
            'password_confirm': 'SecurePass123',
            'roll_number': '2024001',
            'department': 'Computer Science',
            'year_of_study': 1,
        }

        response = self.client.post('/api/auth/register/student/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_faculty_registration(self):
        """Test faculty registration."""
        data = {
            'email': 'faculty@geetauniversity.edu.in',
            'password': 'SecurePass123',
            'password_confirm': 'SecurePass123',
            'employee_id': 'FAC2024001',
            'department': 'Computer Science',
            'designation': 'Assistant Professor',
        }

        response = self.client.post('/api/auth/register/faculty/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email=data['email'])
        self.assertEqual(user.role, User.ROLE_FACULTY)
        self.assertFalse(user.is_faculty_approved)

    def test_password_mismatch(self):
        """Test that password mismatch is rejected."""
        data = {
            'email': 'student@geetauniversity.edu.in',
            'password': 'SecurePass123',
            'password_confirm': 'DifferentPass123',
            'roll_number': '2024001',
            'department': 'Computer Science',
            'year_of_study': 1,
        }

        response = self.client.post('/api/auth/register/student/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class EmailVerificationAPITests(APITestCase):
    """Tests for email verification APIs."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='user@geetauniversity.edu.in',
            password='Pass123',
            is_email_verified=False
        )
        self.otp = EmailOTP.create_otp(self.user.email)

    def test_verify_email(self):
        """Test email verification."""
        data = {
            'email': self.user.email,
            'otp': self.otp.otp
        }

        response = self.client.post('/api/auth/verify-email/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_email_verified)

    def test_verify_email_invalid_otp(self):
        """Test verification with invalid OTP."""
        data = {
            'email': self.user.email,
            'otp': '000000'
        }

        response = self.client.post('/api/auth/verify-email/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_resend_otp(self):
        """Test OTP resending."""
        data = {'email': self.user.email}
        response = self.client.post('/api/auth/resend-otp/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class LoginAPITests(APITestCase):
    """Tests for login APIs."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='user@geetauniversity.edu.in',
            password='SecurePass123',
            is_email_verified=True
        )

    def test_login_success(self):
        """Test successful login."""
        data = {
            'email': 'user@geetauniversity.edu.in',
            'password': 'SecurePass123'
        }

        response = self.client.post('/api/auth/login/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('tokens', response.data)
        self.assertIn('access', response.data['tokens'])

    def test_login_invalid_password(self):
        """Test login with invalid password."""
        data = {
            'email': 'user@geetauniversity.edu.in',
            'password': 'WrongPassword'
        }

        response = self.client.post('/api/auth/login/', data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_unverified_email(self):
        """Test login with unverified email."""
        user = User.objects.create_user(
            email='unverified@geetauniversity.edu.in',
            password='Pass123',
            is_email_verified=False
        )

        data = {
            'email': 'unverified@geetauniversity.edu.in',
            'password': 'Pass123'
        }

        response = self.client.post('/api/auth/login/', data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_brute_force_protection(self):
        """Test brute-force protection on login."""
        data = {
            'email': 'user@geetauniversity.edu.in',
            'password': 'WrongPassword'
        }

        # Make 5 failed attempts
        for _ in range(5):
            self.client.post('/api/auth/login/', data)

        # 6th attempt should be blocked
        response = self.client.post('/api/auth/login/', data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PasswordResetAPITests(APITestCase):
    """Tests for password reset APIs."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='user@geetauniversity.edu.in',
            password='OldPass123'
        )

    def test_password_reset_request(self):
        """Test password reset request."""
        data = {'email': 'user@geetauniversity.edu.in'}
        response = self.client.post('/api/auth/password-reset-request/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_password_reset(self):
        """Test password reset."""
        otp = EmailOTP.create_otp(
            self.user.email,
            purpose='password_reset'
        )

        data = {
            'email': self.user.email,
            'otp': otp.otp,
            'new_password': 'NewPass123',
            'new_password_confirm': 'NewPass123'
        }

        response = self.client.post('/api/auth/password-reset/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewPass123'))

    def test_password_reset_mismatch(self):
        """Test password reset with mismatched passwords."""
        otp = EmailOTP.create_otp(
            self.user.email,
            purpose='password_reset'
        )

        data = {
            'email': self.user.email,
            'otp': otp.otp,
            'new_password': 'NewPass123',
            'new_password_confirm': 'DifferentPass123'
        }

        response = self.client.post('/api/auth/password-reset/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ProfileAPITests(APITestCase):
    """Tests for profile APIs."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='user@geetauniversity.edu.in',
            password='Pass123',
            is_email_verified=True,
            first_name='John',
            last_name='Doe'
        )
        self.client.force_authenticate(user=self.user)

    def test_get_profile(self):
        """Test getting user profile."""
        response = self.client.get('/api/auth/profile/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.user.email)

    def test_update_profile(self):
        """Test updating user profile."""
        data = {
            'first_name': 'Jane',
            'last_name': 'Smith'
        }

        response = self.client.patch('/api/auth/profile/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Jane')
        self.assertEqual(self.user.last_name, 'Smith')

    def test_profile_requires_authentication(self):
        """Test that profile endpoint requires authentication."""
        client = APIClient()
        response = client.get('/api/auth/profile/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserServiceTests(TestCase):
    """Tests for UserService."""

    def setUp(self):
        """Set up test data."""
        self.admin = User.objects.create_superuser(
            email='admin@geetauniversity.edu.in',
            password='AdminPass123'
        )

        self.faculty = User.objects.create_user(
            email='faculty@geetauniversity.edu.in',
            password='FacPass123',
            role=User.ROLE_FACULTY,
            is_email_verified=True
        )
        FacultyProfile.objects.create(
            user=self.faculty,
            employee_id='FAC001',
            department='CS',
            designation='Prof'
        )

    def test_approve_faculty(self):
        """Test faculty approval."""
        self.assertFalse(self.faculty.is_faculty_approved)

        UserService.approve_faculty(self.faculty, self.admin)

        self.faculty.refresh_from_db()
        self.assertTrue(self.faculty.is_faculty_approved)

    def test_reject_faculty(self):
        """Test faculty rejection."""
        UserService.reject_faculty(self.faculty, self.admin)

        profile = self.faculty.faculty_profile
        profile.refresh_from_db()
        self.assertEqual(profile.approval_status, 'rejected')
