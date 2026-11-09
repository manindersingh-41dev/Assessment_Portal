"""
Authentication and email services.

Handles OTP generation, email sending, and business logic for authentication.
"""

import random
import smtplib
from django.core.mail import send_mail
from django.utils import timezone
from django.conf import settings
from datetime import timedelta

from .models import EmailOTP, User, LoginAttempt


class EmailService:
    """Service for sending emails with OTP."""

    @staticmethod
    def send_otp_email(email, otp_code, purpose='email_verification'):
        """
        Send OTP via email.

        Args:
            email (str): Recipient email address
            otp_code (str): 6-digit OTP
            purpose (str): Purpose of OTP (email_verification or password_reset)

        Returns:
            bool: True if sent successfully
        """
        if purpose == 'email_verification':
            subject = 'Email Verification - Geeta University Assessment Portal'
            message = f"""
Hello,

Welcome to Geeta University Coding Assessment Portal!

Your email verification code is: {otp_code}

This code will expire in 10 minutes.

Please do not share this code with anyone.

If you did not request this code, please ignore this email.

Best regards,
Geeta University Portal Team
            """
        elif purpose == 'password_reset':
            subject = 'Password Reset - Geeta University Assessment Portal'
            message = f"""
Hello,

You requested to reset your password.

Your password reset code is: {otp_code}

This code will expire in 10 minutes.

Please do not share this code with anyone.

If you did not request this, please ignore this email.

Best regards,
Geeta University Portal Team
            """
        else:
            return False

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL or 'noreply@geetauniversity.edu.in',
                recipient_list=[email],
                fail_silently=False,
            )
            return True
        except Exception as e:
            print(f"Failed to send email to {email}: {str(e)}")
            return False


class AuthenticationService:
    """Service for authentication operations."""

    OTP_EXPIRY_MINUTES = 10
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_ATTEMPT_WINDOW = 15  # minutes

    @classmethod
    def generate_and_send_otp(cls, email, purpose='email_verification'):
        """
        Generate OTP and send via email.

        Args:
            email (str): Email address
            purpose (str): Purpose of OTP

        Returns:
            EmailOTP: Created OTP record or None
        """
        # Clean up expired OTPs for this email
        EmailOTP.objects.filter(
            email=email,
            purpose=purpose,
            is_used=False,
            expires_at__lt=timezone.now()
        ).delete()

        # Create new OTP
        otp = EmailOTP.create_otp(
            email=email,
            purpose=purpose,
            expires_in_minutes=cls.OTP_EXPIRY_MINUTES
        )

        # Send email
        success = EmailService.send_otp_email(email, otp.otp, purpose)

        if not success:
            otp.delete()
            return None

        return otp

    @classmethod
    def verify_email(cls, email, otp_code):
        """
        Verify email with OTP.

        Args:
            email (str): Email address
            otp_code (str): OTP code

        Returns:
            tuple: (success: bool, user: User or None, message: str)
        """
        try:
            # Find valid OTP
            otp_record = EmailOTP.objects.filter(
                email=email,
                otp=otp_code,
                purpose='email_verification',
                is_used=False
            ).latest('created_at')

            if otp_record.is_expired:
                return False, None, 'OTP has expired'

            # Mark OTP as used
            otp_record.mark_used()

            # Update user
            user = User.objects.get(email=email)
            user.is_email_verified = True
            user.save()

            return True, user, 'Email verified successfully'

        except EmailOTP.DoesNotExist:
            return False, None, 'Invalid OTP'
        except User.DoesNotExist:
            return False, None, 'User not found'

    @classmethod
    def reset_password(cls, email, otp_code, new_password):
        """
        Reset user password with OTP.

        Args:
            email (str): Email address
            otp_code (str): OTP code
            new_password (str): New password

        Returns:
            tuple: (success: bool, user: User or None, message: str)
        """
        try:
            # Find valid OTP
            otp_record = EmailOTP.objects.filter(
                email=email,
                otp=otp_code,
                purpose='password_reset',
                is_used=False
            ).latest('created_at')

            if otp_record.is_expired:
                return False, None, 'OTP has expired'

            # Mark OTP as used
            otp_record.mark_used()

            # Update user password
            user = User.objects.get(email=email)
            user.set_password(new_password)
            user.save()

            return True, user, 'Password reset successfully'

        except EmailOTP.DoesNotExist:
            return False, None, 'Invalid OTP'
        except User.DoesNotExist:
            return False, None, 'User not found'

    @classmethod
    def record_login_attempt(cls, email, ip_address, success=False):
        """
        Record login attempt for brute-force protection.

        Args:
            email (str): Email address
            ip_address (str): IP address
            success (bool): Whether login was successful
        """
        LoginAttempt.objects.create(
            email=email,
            ip_address=ip_address,
            success=success
        )

    @classmethod
    def is_login_blocked(cls, email):
        """
        Check if email has too many failed login attempts.

        Args:
            email (str): Email address

        Returns:
            bool: True if login should be blocked
        """
        return LoginAttempt.is_brute_force(
            email,
            max_attempts=cls.MAX_LOGIN_ATTEMPTS,
            minutes=cls.LOGIN_ATTEMPT_WINDOW
        )

    @classmethod
    def get_failed_attempts_count(cls, email):
        """Get count of failed login attempts."""
        return LoginAttempt.get_failed_attempts(
            email,
            minutes=cls.LOGIN_ATTEMPT_WINDOW
        )


class UserService:
    """Service for user management operations."""

    @classmethod
    def approve_faculty(cls, faculty_user, approved_by_user):
        """
        Approve faculty account.

        Args:
            faculty_user (User): Faculty user to approve
            approved_by_user (User): Admin user approving

        Returns:
            bool: Success status
        """
        if not faculty_user.is_faculty():
            return False

        try:
            faculty_profile = faculty_user.faculty_profile
            faculty_profile.approval_status = 'approved'
            faculty_profile.approved_by = approved_by_user
            faculty_profile.approval_date = timezone.now()
            faculty_profile.save()

            faculty_user.is_faculty_approved = True
            faculty_user.save()

            return True
        except Exception:
            return False

    @classmethod
    def reject_faculty(cls, faculty_user, rejected_by_user):
        """
        Reject faculty account.

        Args:
            faculty_user (User): Faculty user to reject
            rejected_by_user (User): Admin user rejecting

        Returns:
            bool: Success status
        """
        if not faculty_user.is_faculty():
            return False

        try:
            faculty_profile = faculty_user.faculty_profile
            faculty_profile.approval_status = 'rejected'
            faculty_profile.approved_by = rejected_by_user
            faculty_profile.approval_date = timezone.now()
            faculty_profile.save()

            return True
        except Exception:
            return False

    @classmethod
    def get_pending_faculty_approvals(cls):
        """Get all faculty users pending approval."""
        return User.objects.filter(
            role=User.ROLE_FACULTY,
            is_faculty_approved=False
        ).select_related('faculty_profile')

    @classmethod
    def deactivate_user(cls, user):
        """Deactivate user account."""
        user.is_active = False
        user.save()
        return True

    @classmethod
    def activate_user(cls, user):
        """Activate user account."""
        user.is_active = True
        user.save()
        return True
