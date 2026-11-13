"""
Views for user authentication and profile management.

Implements API endpoints for registration, email verification, login,
password reset, and profile management.
"""

import logging
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.core import signing
from django.core.validators import validate_email
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import User, StudentProfile, FacultyProfile, LoginAttempt
from .serializers import (
    StudentRegistrationSerializer,
    FacultyRegistrationSerializer,
    EmailVerificationSerializer,
    LoginSerializer,
    PasswordResetRequestSerializer,
    PasswordResetSerializer,
    UserProfileSerializer,
    ProfileUpdateSerializer,
    StudentProfileSerializer,
    FacultyProfileSerializer,
    FacultyAssessmentPreferenceSerializer,
)
from .services import AuthenticationService, UserService
from .permissions import IsStudent, IsFaculty, IsAdmin, IsEmailVerified, IsApprovedFaculty

logger = logging.getLogger(__name__)


def _registration_conflict_details(error):
    """Translate database uniqueness conflicts into useful field errors."""
    message = str(error).lower()
    if 'email' in message:
        return {'email': ['This email is already registered.']}
    if 'roll_number' in message:
        return {'roll_number': ['This roll number is already registered.']}
    if 'employee_id' in message:
        return {'employee_id': ['This employee ID is already registered.']}
    return {
        'registration': [
            'Some submitted information is already in use. Check the email and student or employee ID.'
        ]
    }


class StudentDirectorySerializer(serializers.ModelSerializer):
    """Minimal student information needed for assessment assignment."""

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name"]


class StudentDirectoryView(APIView):
    """Return the student directory to approved faculty members."""

    permission_classes = [IsApprovedFaculty]

    def get(self, request):
        if request.query_params.get("role", "student") != "student":
            return Response(
                {"detail": "Only the student directory is available here."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        students = User.objects.filter(
            role=User.ROLE_STUDENT, is_active=True
        ).order_by("last_name", "first_name", "email")
        return Response(StudentDirectorySerializer(students, many=True).data)


class ClearStudentLoginLockView(APIView):
    """Let approved faculty clear a student's active login lockout."""

    permission_classes = [IsApprovedFaculty]

    def post(self, request, student_id):
        try:
            student = User.objects.get(
                pk=student_id,
                role=User.ROLE_STUDENT,
            )
        except User.DoesNotExist:
            return Response(
                {"detail": "Student not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        cutoff = timezone.now() - timedelta(
            minutes=AuthenticationService.LOGIN_ATTEMPT_WINDOW
        )
        recent_failures = LoginAttempt.objects.filter(
            email__iexact=student.email,
            success=False,
            attempted_at__gte=cutoff,
        )
        cleared_attempts = recent_failures.count()
        recent_failures.delete()

        logger.info(
            "Faculty user %s cleared %s recent failed login attempts for student %s",
            request.user.pk,
            cleared_attempts,
            student.pk,
        )
        return Response(
            {
                "detail": "Student login lock cleared.",
                "cleared_attempts": cleared_attempts,
            },
            status=status.HTTP_200_OK,
        )


class RegisterStudentView(viewsets.ViewSet):
    """Endpoint for student registration."""

    permission_classes = [AllowAny]

    def create(self, request):
        """
        Register a new student.

        POST /api/auth/register/student/
        {
            "email": "john.doe@geetauniversity.edu.in",
            "password": "SecurePass123",
            "password_confirm": "SecurePass123",
            "roll_number": "2024001",
            "department": "Computer Science",
            "year_of_study": 1,
            "first_name": "John",  # Optional, extracted from email if not provided
            "last_name": "Doe"     # Optional, extracted from email if not provided
        }
        """
        serializer = StudentRegistrationSerializer(data=request.data)

        if serializer.is_valid():
            try:
                with transaction.atomic():
                    user = serializer.save()

                    # Generate and send OTP
                    otp = AuthenticationService.generate_and_send_otp(
                        user.email,
                        purpose='email_verification'
                    )

                    if not otp:
                        # Clean up user if OTP sending fails
                        user.delete()
                        return Response(
                            {
                                'error': 'Failed to send verification email. Please try again.',
                                'details': 'Email service is temporarily unavailable'
                            },
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR
                        )

                    return Response(
                        {
                            'message': 'Student registered successfully',
                            'email': user.email,
                            'next_step': 'Verify your email with the OTP sent to your email address',
                            'details': {
                                'user_id': str(user.id),
                                'role': user.role,
                                'email_verified': user.is_email_verified
                            }
                        },
                        status=status.HTTP_201_CREATED
                    )
            except IntegrityError as e:
                return Response(
                    {
                        'error': 'Registration conflicts with an existing account or profile.',
                        'details': _registration_conflict_details(e),
                    },
                    status=status.HTTP_409_CONFLICT
                )
            except Exception:
                logger.exception('Unexpected student registration failure')
                return Response(
                    {
                        'error': 'Student registration failed.',
                        'details': 'An unexpected server error occurred. Please try again. If it continues, contact support.',
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            validation_errors = serializer.errors
            duplicate_email = any(
                getattr(error, 'code', None) == 'already_registered'
                for error in validation_errors.get('email', [])
            )
            return Response(
                {
                    'error': (
                        'This email is already registered.'
                        if duplicate_email
                        else 'Please correct the registration details.'
                    ),
                    'details': validation_errors,
                },
                status=(
                    status.HTTP_409_CONFLICT
                    if duplicate_email
                    else status.HTTP_400_BAD_REQUEST
                )
            )


class RegisterFacultyView(viewsets.ViewSet):
    """Endpoint for faculty registration."""

    permission_classes = [AllowAny]

    def create(self, request):
        """
        Register a new faculty member (pending administrator approval).

        POST /api/auth/register/faculty/
        {
            "email": "jane.smith@geetauniversity.edu.in",
            "password": "SecurePass123",
            "password_confirm": "SecurePass123",
            "employee_id": "FAC2024001",
            "department": "Computer Science",
            "designation": "Assistant Professor",
            "first_name": "Jane",  # Optional
            "last_name": "Smith"   # Optional
        }
        """
        serializer = FacultyRegistrationSerializer(data=request.data)

        if serializer.is_valid():
            try:
                with transaction.atomic():
                    user = serializer.save()

                    # Generate and send OTP
                    otp = AuthenticationService.generate_and_send_otp(
                        user.email,
                        purpose='email_verification'
                    )

                    if not otp:
                        user.delete()
                        return Response(
                            {
                                'error': 'Failed to send verification email',
                                'details': 'Email service is temporarily unavailable'
                            },
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR
                        )

                    return Response(
                        {
                            'message': 'Faculty registered successfully',
                            'email': user.email,
                            'next_step': 'Verify your email and wait for administrator approval',
                            'details': {
                                'user_id': str(user.id),
                                'role': user.role,
                                'email_verified': user.is_email_verified,
                                'approval_status': 'pending'
                            }
                        },
                        status=status.HTTP_201_CREATED
                    )
            except IntegrityError as e:
                return Response(
                    {
                        'error': 'Registration conflicts with an existing account or profile.',
                        'details': _registration_conflict_details(e),
                    },
                    status=status.HTTP_409_CONFLICT
                )
            except Exception:
                logger.exception('Unexpected faculty registration failure')
                return Response(
                    {
                        'error': 'Faculty registration failed.',
                        'details': 'An unexpected server error occurred. Please try again. If it continues, contact support.',
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            validation_errors = serializer.errors
            duplicate_email = any(
                getattr(error, 'code', None) == 'already_registered'
                for error in validation_errors.get('email', [])
            )
            return Response(
                {
                    'error': (
                        'This email is already registered.'
                        if duplicate_email
                        else 'Please correct the registration details.'
                    ),
                    'details': validation_errors,
                },
                status=(
                    status.HTTP_409_CONFLICT
                    if duplicate_email
                    else status.HTTP_400_BAD_REQUEST
                )
            )


class VerifyEmailView(viewsets.ViewSet):
    """Endpoint for email verification."""

    permission_classes = [AllowAny]

    def create(self, request):
        """
        Verify email with OTP.

        POST /api/auth/verify-email/
        {
            "email": "john.doe@geetauniversity.edu.in",
            "otp": "123456"
        }
        """
        serializer = EmailVerificationSerializer(data=request.data)

        if serializer.is_valid():
            otp_record = serializer.validated_data['otp_record']
            login_challenge = serializer.validated_data.get('login_challenge')
            challenge_user_id = None
            if login_challenge:
                try:
                    challenge_data = signing.loads(
                        login_challenge,
                        salt='users.login-verification',
                        max_age=AuthenticationService.OTP_EXPIRY_MINUTES * 60,
                    )
                    if challenge_data.get('purpose') != 'email_verification_login':
                        raise signing.BadSignature('Invalid login verification purpose')
                    challenge_user_id = challenge_data.get('user_id')
                    if not challenge_user_id:
                        raise signing.BadSignature('Missing user in login verification challenge')
                except (signing.BadSignature, TypeError, ValueError):
                    return Response(
                        {
                            'error': 'Your login verification session expired.',
                            'details': 'Sign in again to receive a new verification code.',
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

            try:
                with transaction.atomic():
                    user = User.objects.get(email=serializer.validated_data['email'])
                    if challenge_user_id and challenge_user_id != str(user.id):
                        return Response(
                            {
                                'error': 'This verification code does not match the login session.',
                                'details': 'Sign in again with the account you are verifying.',
                            },
                            status=status.HTTP_400_BAD_REQUEST
                        )

                    user.is_email_verified = True
                    user.save()

                    otp_record.mark_used()

                    response_data = {
                        'message': 'Email verified successfully',
                        'email': user.email,
                        'auto_login': False,
                        'next_step': 'You can now login with your credentials',
                    }

                    can_login_after_verification = (
                        challenge_user_id is not None
                        and user.is_active
                        and not (user.is_faculty() and not user.is_faculty_approved)
                    )

                    if can_login_after_verification:
                        refresh = RefreshToken.for_user(user)
                        response_data.update({
                            'auto_login': True,
                            'user': {
                                'id': str(user.id),
                                'email': user.email,
                                'name': user.get_full_name(),
                                'role': user.role,
                            },
                            'tokens': {
                                'access': str(refresh.access_token),
                                'refresh': str(refresh),
                            },
                        })
                        response_data['next_step'] = 'Email verified and signed in successfully'
                    elif challenge_user_id and user.is_faculty() and not user.is_faculty_approved:
                        response_data['next_step'] = (
                            'Email verified. Your faculty account is waiting for administrator approval.'
                        )

                    return Response(response_data, status=status.HTTP_200_OK)
            except Exception as e:
                return Response(
                    {'error': 'Email verification failed', 'details': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResendOTPView(viewsets.ViewSet):
    """Endpoint to resend OTP."""

    permission_classes = [AllowAny]

    def create(self, request):
        """
        Resend OTP to email.

        POST /api/auth/resend-otp/
        {
            "email": "john.doe@geetauniversity.edu.in",
            "purpose": "email_verification"  # or "password_reset"
        }
        """
        email = request.data.get('email')
        purpose = request.data.get('purpose', 'email_verification')

        if not email:
            return Response(
                {'error': 'Email is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if purpose not in ['email_verification', 'password_reset']:
            return Response(
                {'error': 'Invalid purpose'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)

            if purpose == 'email_verification' and user.is_email_verified:
                return Response(
                    {'message': 'Email is already verified'},
                    status=status.HTTP_200_OK
                )

            otp = AuthenticationService.generate_and_send_otp(email, purpose)

            if not otp:
                return Response(
                    {'error': 'Failed to send OTP'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            return Response(
                {
                    'message': 'OTP sent successfully',
                    'email': email,
                    'expires_in_minutes': AuthenticationService.OTP_EXPIRY_MINUTES
                },
                status=status.HTTP_200_OK
            )
        except User.DoesNotExist:
            return Response(
                {'error': 'No user found with this email'},
                status=status.HTTP_404_NOT_FOUND
            )


class LoginView(viewsets.ViewSet):
    """Endpoint for user login."""

    permission_classes = [AllowAny]

    def create(self, request):
        """
        Login with email and password.

        POST /api/auth/login/
        {
            "email": "john.doe@geetauniversity.edu.in",
            "password": "SecurePass123"
        }
        """
        serializer = LoginSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.validated_data['user']

            # Get client IP for logging
            ip_address = self._get_client_ip(request)

            if serializer.validated_data.get('email_verification_pending'):
                try:
                    AuthenticationService.record_login_attempt(
                        user.email,
                        ip_address,
                        success=True
                    )
                    otp = AuthenticationService.generate_and_send_otp(
                        user.email,
                        purpose='email_verification'
                    )
                except Exception:
                    logger.exception(
                        'Could not issue login verification OTP for %s',
                        user.email,
                    )
                    otp = None

                if not otp:
                    return Response(
                        {
                            'error': 'Could not send a verification code.',
                            'details': 'Please try signing in again. If the problem continues, contact support.',
                        },
                        status=status.HTTP_503_SERVICE_UNAVAILABLE
                    )

                return Response(
                    {
                        'verification_required': True,
                        'message': 'Your email is not verified. A new verification code has been sent.',
                        'email': user.email,
                        'role': user.role,
                        'expires_in_minutes': AuthenticationService.OTP_EXPIRY_MINUTES,
                        'login_challenge': signing.dumps(
                            {
                                'user_id': str(user.id),
                                'purpose': 'email_verification_login',
                            },
                            salt='users.login-verification',
                        ),
                    },
                    status=status.HTTP_202_ACCEPTED
                )

            try:
                with transaction.atomic():
                    # Record successful login
                    AuthenticationService.record_login_attempt(
                        user.email,
                        ip_address,
                        success=True
                    )

                    # Generate JWT tokens
                    refresh = RefreshToken.for_user(user)

                    return Response(
                        {
                            'message': 'Login successful',
                            'user': {
                                'id': str(user.id),
                                'email': user.email,
                                'name': user.get_full_name(),
                                'role': user.role,
                            },
                            'tokens': {
                                'access': str(refresh.access_token),
                                'refresh': str(refresh),
                            }
                        },
                        status=status.HTTP_200_OK
                    )
            except Exception as e:
                return Response(
                    {'error': 'Login failed', 'details': str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            email = request.data.get('email')
            ip_address = self._get_client_ip(request)

            if isinstance(email, str) and email.strip():
                # Match the normalized email used by LoginSerializer so
                # casing or surrounding spaces cannot split the attempt count.
                email = email.strip().lower()
                try:
                    validate_email(email)
                except ValidationError:
                    pass
                else:
                    # Failed requests made while blocked must not become new
                    # failures: the lockout expires when the first failure in
                    # the active 15-minute window ages out.
                    if not LoginAttempt.is_brute_force(email):
                        AuthenticationService.record_login_attempt(
                            email,
                            ip_address,
                            success=False
                        )

            return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)

    @staticmethod
    def _get_client_ip(request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class LogoutView(viewsets.ViewSet):
    """Endpoint for user logout."""

    permission_classes = [IsAuthenticated]

    def create(self, request):
        """
        Logout user (token blacklisting).

        POST /api/auth/logout/
        """
        try:
            refresh_token = request.data.get('refresh_token')

            if refresh_token:
                try:
                    token = RefreshToken(refresh_token)
                    token.blacklist()
                except Exception:
                    pass

            return Response(
                {'message': 'Logout successful'},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': 'Logout failed', 'details': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class PasswordResetRequestView(viewsets.ViewSet):
    """Endpoint to request password reset."""

    permission_classes = [AllowAny]

    def create(self, request):
        """
        Request password reset OTP.

        POST /api/auth/password-reset-request/
        {
            "email": "john.doe@geetauniversity.edu.in"
        }
        """
        serializer = PasswordResetRequestSerializer(data=request.data)

        if serializer.is_valid():
            email = serializer.validated_data['email']

            otp = AuthenticationService.generate_and_send_otp(
                email,
                purpose='password_reset'
            )

            if not otp:
                return Response(
                    {'error': 'Failed to send reset email'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            return Response(
                {
                    'message': 'Password reset OTP sent to email',
                    'email': email,
                    'expires_in_minutes': AuthenticationService.OTP_EXPIRY_MINUTES
                },
                status=status.HTTP_200_OK
            )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetView(viewsets.ViewSet):
    """Endpoint for password reset."""

    permission_classes = [AllowAny]

    def create(self, request):
        """
        Reset password with OTP.

        POST /api/auth/password-reset/
        {
            "email": "john.doe@geetauniversity.edu.in",
            "otp": "123456",
            "new_password": "NewSecurePass123",
            "new_password_confirm": "NewSecurePass123"
        }
        """
        serializer = PasswordResetSerializer(data=request.data)

        if serializer.is_valid():
            otp_record = serializer.validated_data['otp_record']
            try:
                with transaction.atomic():
                    user = User.objects.get(email=serializer.validated_data['email'])
                    user.set_password(serializer.validated_data['new_password'])
                    user.save()

                    otp_record.mark_used()

                    return Response(
                        {
                            'message': 'Password reset successfully',
                            'next_step': 'You can now login with your new password'
                        },
                        status=status.HTTP_200_OK
                    )
            except Exception as e:
                return Response(
                    {'error': 'Password reset failed', 'details': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(viewsets.ViewSet):
    """Endpoint for user profile management."""

    permission_classes = [IsAuthenticated, IsEmailVerified]

    def retrieve(self, request, pk=None):
        """
        Get current user profile.

        GET /api/auth/profile/
        """
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def partial_update(self, request, pk=None):
        """
        Update current user profile.

        PATCH /api/auth/profile/
        {
            "first_name": "John",
            "last_name": "Doe"
        }
        """
        serializer = ProfileUpdateSerializer(
            request.user,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    'message': 'Profile updated successfully',
                    'profile': UserProfileSerializer(request.user).data
                },
                status=status.HTTP_200_OK
            )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StudentProfileView(viewsets.ViewSet):
    """Endpoint for student profile management."""

    permission_classes = [IsAuthenticated, IsEmailVerified, IsStudent]

    def retrieve(self, request):
        """
        Get student profile.

        GET /api/auth/profile/student/
        """
        try:
            profile = request.user.student_profile
            serializer = StudentProfileSerializer(profile)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except StudentProfile.DoesNotExist:
            return Response(
                {'error': 'Student profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class FacultyProfileView(viewsets.ViewSet):
    """Endpoint for faculty profile management."""

    permission_classes = [IsAuthenticated, IsEmailVerified, IsFaculty]

    def retrieve(self, request, pk=None):
        """
        Get faculty profile.

        GET /api/auth/profile/faculty/
        """
        try:
            profile = request.user.faculty_profile
            serializer = FacultyProfileSerializer(profile)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except FacultyProfile.DoesNotExist:
            return Response(
                {'error': 'Faculty profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    def partial_update(self, request, pk=None):
        """Save faculty preferences used as defaults in new assessments."""
        try:
            profile = request.user.faculty_profile
        except FacultyProfile.DoesNotExist:
            return Response(
                {'error': 'Faculty profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = FacultyAssessmentPreferenceSerializer(
            profile,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            'message': 'Assessment preferences saved.',
            'profile': FacultyProfileSerializer(profile).data,
        }, status=status.HTTP_200_OK)
