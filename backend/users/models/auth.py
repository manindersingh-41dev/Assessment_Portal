"""
Authentication and user models for Geeta University Coding Assessment Portal.

Custom user model with email-based authentication, OTP verification,
and role-based access control.
"""

import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator, EmailValidator
from django.utils import timezone
from datetime import timedelta


class CustomUserManager(BaseUserManager):
    """Custom user manager for email-based authentication."""

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user."""
        if not email:
            raise ValueError("Email address is required")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "faculty")
        extra_fields.setdefault("is_email_verified", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom user model with email-based authentication.

    Extends Django's AbstractUser to use email as the primary identifier
    instead of username. Implements role-based access control and OTP verification.
    """

    ROLE_STUDENT = "student"
    ROLE_FACULTY = "faculty"

    ROLE_CHOICES = [
        (ROLE_STUDENT, "Student"),
        (ROLE_FACULTY, "Faculty"),
    ]

    # UUID as primary key for security
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Email as the unique identifier (replaces username)
    email = models.EmailField(
        unique=True,
        validators=[
            EmailValidator(),
            RegexValidator(
                regex=r'^[a-zA-Z0-9._%+-]+@geetauniversity\.edu\.in$',
                message='Email must be from @geetauniversity.edu.in domain',
                code='invalid_university_email',
            )
        ]
    )

    # User profile fields
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)

    # Role-based access control
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_STUDENT,
        help_text="User role determines access permissions"
    )

    # Email verification
    is_email_verified = models.BooleanField(
        default=False,
        help_text="User must verify email before using the system"
    )

    # Faculty approval (only faculty need approval)
    is_faculty_approved = models.BooleanField(
        default=False,
        help_text="Faculty must be approved by administrator"
    )

    # Account status
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive users cannot login"
    )

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)

    # Manager
    objects = CustomUserManager()

    # Use email instead of username
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    # Remove username field since we use email
    username = None

    class Meta:
        db_table = "users_user"
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['is_email_verified']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.get_full_name() or self.email} ({self.get_role_display()})"

    def get_full_name(self):
        """Return user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name or ""

    def is_student(self):
        """Check if user is a student."""
        return self.role == self.ROLE_STUDENT

    def is_faculty(self):
        """Check if user is faculty."""
        return self.role == self.ROLE_FACULTY

    def can_use_system(self):
        """Check if user can use the system."""
        return self.is_active and self.is_email_verified

    def can_submit_code(self):
        """Check if user can submit code (students only)."""
        return self.is_student() and self.can_use_system()

    def can_manage_assessments(self):
        """Check if user can manage assessments (faculty only)."""
        return self.is_faculty() and self.can_use_system() and self.is_faculty_approved


class EmailOTP(models.Model):
    """
    Email OTP verification model.

    Stores one-time passwords sent to user emails for verification.
    OTPs expire after a configured duration.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField()
    otp = models.CharField(
        max_length=6,
        validators=[RegexValidator(r'^\d{6}$', 'OTP must be 6 digits')]
    )
    purpose = models.CharField(
        max_length=50,
        choices=[
            ('email_verification', 'Email Verification'),
            ('password_reset', 'Password Reset'),
        ],
        default='email_verification'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "users_emailotp"
        indexes = [
            models.Index(fields=['email', 'is_used']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"OTP for {self.email} ({self.purpose})"

    @property
    def is_expired(self):
        """Check if OTP has expired."""
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        """Check if OTP is valid (not used and not expired)."""
        return not self.is_used and not self.is_expired

    def mark_used(self):
        """Mark OTP as used."""
        self.is_used = True
        self.used_at = timezone.now()
        self.save()

    @classmethod
    def create_otp(cls, email, purpose='email_verification', expires_in_minutes=10):
        """Create a new OTP for the given email."""
        import random

        # Generate 6-digit OTP
        otp_code = str(random.randint(100000, 999999))

        # Calculate expiry time
        expires_at = timezone.now() + timedelta(minutes=expires_in_minutes)

        # Create OTP record
        otp = cls.objects.create(
            email=email,
            otp=otp_code,
            purpose=purpose,
            expires_at=expires_at
        )
        return otp


class StudentProfile(models.Model):
    """
    Student-specific profile information.

    Linked to User model with OneToOne relationship.
    Stores university-specific student data.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='student_profile',
        limit_choices_to={'role': User.ROLE_STUDENT}
    )
    roll_number = models.CharField(max_length=50, unique=True)
    department = models.CharField(max_length=100)
    year_of_study = models.IntegerField(
        choices=[(i, f'Year {i}') for i in range(1, 5)],
        default=1
    )
    phone_number = models.CharField(max_length=20, blank=True)
    enrollment_date = models.DateField(auto_now_add=False, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users_studentprofile"
        indexes = [
            models.Index(fields=['roll_number']),
            models.Index(fields=['department']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.roll_number}"


class FacultyProfile(models.Model):
    """
    Faculty-specific profile information.

    Linked to User model with OneToOne relationship.
    Stores university-specific faculty data.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='faculty_profile',
        limit_choices_to={'role': User.ROLE_FACULTY}
    )
    employee_id = models.CharField(max_length=50, unique=True)
    department = models.CharField(max_length=100)
    designation = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20, blank=True)
    joining_date = models.DateField(auto_now_add=False, null=True, blank=True)
    default_assessment_is_timed = models.BooleanField(
        default=True,
        help_text="Default timer setting for new assessments created by this faculty member.",
    )

    # Approval tracking
    approval_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending Approval'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        default='pending'
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_faculty'
    )
    approval_date = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users_facultyprofile"
        indexes = [
            models.Index(fields=['employee_id']),
            models.Index(fields=['department']),
            models.Index(fields=['approval_status']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.employee_id} ({self.get_approval_status_display()})"

    def is_approved(self):
        """Check if faculty is approved."""
        return self.approval_status == 'approved'


class LoginAttempt(models.Model):
    """
    Track login attempts for brute-force protection.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField()
    ip_address = models.GenericIPAddressField()
    success = models.BooleanField(default=False)
    attempted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "users_loginattempt"
        indexes = [
            models.Index(fields=['email', 'attempted_at']),
            models.Index(fields=['ip_address', 'attempted_at']),
        ]

    def __str__(self):
        status = "Success" if self.success else "Failed"
        return f"{status} login attempt for {self.email} from {self.ip_address}"

    @classmethod
    def get_failed_attempts(cls, email, minutes=15):
        """Get failed login attempts in the last N minutes."""
        cutoff_time = timezone.now() - timedelta(minutes=minutes)
        return cls.objects.filter(
            email=email,
            success=False,
            attempted_at__gte=cutoff_time
        ).count()

    @classmethod
    def is_brute_force(cls, email, max_attempts=5, minutes=15):
        """Check if email has exceeded max failed attempts."""
        failed_attempts = cls.get_failed_attempts(email, minutes)
        return failed_attempts >= max_attempts
