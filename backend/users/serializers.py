"""
Serializers for user authentication and profile management.

Implements validation, data transformation, and API request/response handling
for registration, login, password reset, and profile management.
"""

from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils import timezone
from datetime import timedelta
import re

from .models import User, StudentProfile, FacultyProfile, EmailOTP


class EmailValidator(serializers.EmailField):
    """Custom email validator for university email domain."""

    def run_validation(self, data):
        """Validate that email is from @geetauniversity.edu.in domain."""
        data = super().run_validation(data)
        data = data.strip().lower()
        if not data.endswith('@geetauniversity.edu.in'):
            raise serializers.ValidationError(
                'Email must be from @geetauniversity.edu.in domain'
            )
        return data


class NameExtractor:
    """
    Utility to extract name from university email address.

    Supports various email naming conventions:
    - firstname.lastname@geetauniversity.edu.in
    - firstname.lastnameYYYY@geetauniversity.edu.in
    - firstnamelastname@geetauniversity.edu.in
    """

    @staticmethod
    def extract_name(email):
        """
        Extract first and last name from email.

        Returns:
            dict: {'first_name': str, 'last_name': str}
        """
        # Extract the part before @
        local_part = email.split('@')[0].lower()

        # Try pattern: firstname.lastname or firstname.lastname2024
        if '.' in local_part:
            parts = local_part.split('.')
            if len(parts) >= 2:
                first_name = parts[0].strip()
                # Remove any trailing digits from last name
                last_name = re.sub(r'\d+$', '', parts[1]).strip()

                if first_name and last_name:
                    return {
                        'first_name': first_name.capitalize(),
                        'last_name': last_name.capitalize(),
                    }

        # Fallback: return empty, user should provide manually
        return {'first_name': '', 'last_name': ''}


class StudentRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for student registration."""

    email = EmailValidator()
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        help_text='Password must be at least 8 characters',
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )
    roll_number = serializers.CharField(max_length=50, required=True)
    department = serializers.CharField(max_length=100, required=True)
    year_of_study = serializers.IntegerField(required=True)
    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            'email', 'password', 'password_confirm',
            'first_name', 'last_name',
            'roll_number', 'department', 'year_of_study'
        ]

    def validate_password(self, value):
        """Validate password strength."""
        if len(value) < 8:
            raise serializers.ValidationError(
                'Password must be at least 8 characters'
            )
        if value.isdigit():
            raise serializers.ValidationError(
                'Password cannot be entirely numeric'
            )
        return value

    def validate_email(self, value):
        """Return a clear conflict when this email already has an account."""
        normalized_email = value.strip().lower()
        if User.objects.filter(email__iexact=normalized_email).exists():
            raise serializers.ValidationError(
                'This email is already registered.',
                code='already_registered',
            )
        return normalized_email

    def validate(self, data):
        """Validate that passwords match and extract name if not provided."""
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'Passwords do not match'
            })

        # Extract name from email if not provided
        if not data.get('first_name') or not data.get('last_name'):
            extracted = NameExtractor.extract_name(data['email'])
            data['first_name'] = data.get('first_name') or extracted['first_name']
            data['last_name'] = data.get('last_name') or extracted['last_name']

        return data

    def create(self, validated_data):
        """Create user and student profile."""
        validated_data.pop('password_confirm')

        # Extract profile data
        roll_number = validated_data.pop('roll_number')
        department = validated_data.pop('department')
        year_of_study = validated_data.pop('year_of_study')

        # Create user
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            role=User.ROLE_STUDENT,
            is_email_verified=False,
        )

        # Create student profile
        StudentProfile.objects.create(
            user=user,
            roll_number=roll_number,
            department=department,
            year_of_study=year_of_study
        )

        return user


class FacultyRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for faculty registration (pending approval)."""

    email = EmailValidator()
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )
    employee_id = serializers.CharField(max_length=50, required=True)
    department = serializers.CharField(max_length=100, required=True)
    designation = serializers.CharField(max_length=100, required=True)
    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            'email', 'password', 'password_confirm',
            'first_name', 'last_name',
            'employee_id', 'department', 'designation'
        ]

    def validate_password(self, value):
        """Validate password strength."""
        if len(value) < 8:
            raise serializers.ValidationError(
                'Password must be at least 8 characters'
            )
        if value.isdigit():
            raise serializers.ValidationError(
                'Password cannot be entirely numeric'
            )
        return value

    def validate_email(self, value):
        """Return a clear conflict when this email already has an account."""
        normalized_email = value.strip().lower()
        if User.objects.filter(email__iexact=normalized_email).exists():
            raise serializers.ValidationError(
                'This email is already registered.',
                code='already_registered',
            )
        return normalized_email

    def validate(self, data):
        """Validate that passwords match and extract name if not provided."""
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'Passwords do not match'
            })

        # Extract name from email if not provided
        if not data.get('first_name') or not data.get('last_name'):
            extracted = NameExtractor.extract_name(data['email'])
            data['first_name'] = data.get('first_name') or extracted['first_name']
            data['last_name'] = data.get('last_name') or extracted['last_name']

        return data

    def create(self, validated_data):
        """Create user and faculty profile."""
        validated_data.pop('password_confirm')

        # Extract profile data
        employee_id = validated_data.pop('employee_id')
        department = validated_data.pop('department')
        designation = validated_data.pop('designation')

        # Create user (not approved by default)
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            role=User.ROLE_FACULTY,
            is_email_verified=False,
            is_faculty_approved=False,  # Requires admin approval
        )

        # Create faculty profile
        FacultyProfile.objects.create(
            user=user,
            employee_id=employee_id,
            department=department,
            designation=designation,
            approval_status='pending'
        )

        return user


class EmailVerificationSerializer(serializers.Serializer):
    """Serializer for email OTP verification."""

    email = EmailValidator()
    login_challenge = serializers.CharField(
        required=False,
        write_only=True,
        allow_blank=True,
        max_length=1024,
    )
    otp = serializers.CharField(
        max_length=6,
        min_length=6,
        help_text='6-digit OTP sent to email'
    )

    def validate_otp(self, value):
        """Validate OTP format."""
        if not value.isdigit():
            raise serializers.ValidationError('OTP must contain only digits')
        return value

    def validate(self, data):
        """Validate OTP is valid and matches email."""
        try:
            otp_record = EmailOTP.objects.filter(
                email=data['email'],
                otp=data['otp'],
                purpose='email_verification'
            ).latest('created_at')

            if not otp_record.is_valid:
                raise serializers.ValidationError('Invalid or expired OTP')

        except EmailOTP.DoesNotExist:
            raise serializers.ValidationError('Invalid OTP')

        data['otp_record'] = otp_record
        return data


class LoginSerializer(serializers.Serializer):
    """Serializer for user login."""

    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate_email(self, value):
        """Normalize email for authentication and failed-attempt tracking."""
        return value.strip().lower()

    def validate(self, data):
        """Validate credentials and check brute-force protection."""
        email = data.get('email')
        password = data.get('password')

        # Check brute-force protection
        from .models import LoginAttempt
        if LoginAttempt.is_brute_force(email):
            raise serializers.ValidationError(
                'Too many login attempts. Try again later.'
            )

        # Authenticate user
        user = authenticate(username=email, password=password)

        if not user:
            raise serializers.ValidationError('Invalid email or password')

        # Check if user is active
        if not user.is_active:
            raise serializers.ValidationError('User account is inactive')

        # Allow the login view to issue a fresh verification code for accounts
        # with valid credentials whose email has not yet been verified.
        if not user.is_email_verified:
            data['user'] = user
            data['email_verification_pending'] = True
            return data

        # Check faculty approval if applicable
        if user.is_faculty() and not user.is_faculty_approved:
            raise serializers.ValidationError(
                'Your faculty account is pending administrator approval'
            )

        data['user'] = user
        return data


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for password reset request."""

    email = serializers.EmailField()

    def validate_email(self, value):
        """Check if user exists."""
        try:
            User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError('No user found with this email')
        return value


class PasswordResetSerializer(serializers.Serializer):
    """Serializer for password reset with OTP."""

    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6, min_length=6)
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate_otp(self, value):
        """Validate OTP format."""
        if not value.isdigit():
            raise serializers.ValidationError('OTP must contain only digits')
        return value

    def validate_new_password(self, value):
        """Validate new password strength."""
        if value.isdigit():
            raise serializers.ValidationError(
                'Password cannot be entirely numeric'
            )
        return value

    def validate(self, data):
        """Validate OTP and passwords match."""
        # Validate OTP
        try:
            otp_record = EmailOTP.objects.filter(
                email=data['email'],
                otp=data['otp'],
                purpose='password_reset'
            ).latest('created_at')

            if not otp_record.is_valid:
                raise serializers.ValidationError({'otp': 'Invalid or expired OTP'})

        except EmailOTP.DoesNotExist:
            raise serializers.ValidationError({'otp': 'Invalid OTP'})

        # Validate passwords match
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': 'Passwords do not match'
            })

        data['otp_record'] = otp_record
        return data


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile display."""

    role_display = serializers.CharField(source='get_role_display', read_only=True)
    full_name = serializers.SerializerMethodField()
    can_submit_code = serializers.SerializerMethodField()
    can_manage_assessments = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'full_name', 'first_name', 'last_name',
            'role', 'role_display',
            'is_email_verified', 'is_faculty_approved',
            'is_active', 'created_at', 'updated_at',
            'can_submit_code', 'can_manage_assessments'
        ]
        read_only_fields = [
            'id', 'email', 'role', 'is_email_verified', 'is_faculty_approved',
            'created_at', 'updated_at'
        ]

    def get_full_name(self, obj):
        """Get user's full name."""
        return obj.get_full_name()

    def get_can_submit_code(self, obj):
        """Check if user can submit code."""
        return obj.can_submit_code()

    def get_can_manage_assessments(self, obj):
        """Check if user can manage assessments."""
        return obj.can_manage_assessments()


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile."""

    class Meta:
        model = User
        fields = ['first_name', 'last_name']

    def update(self, instance, validated_data):
        """Update user profile."""
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.save()
        return instance


class StudentProfileSerializer(serializers.ModelSerializer):
    """Serializer for student profile display."""

    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = StudentProfile
        fields = [
            'id', 'user_email', 'user_name',
            'roll_number', 'department', 'year_of_study',
            'phone_number', 'enrollment_date',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'enrollment_date', 'created_at', 'updated_at']

    def get_user_name(self, obj):
        """Get user's full name."""
        return obj.user.get_full_name()


class FacultyProfileSerializer(serializers.ModelSerializer):
    """Serializer for faculty profile display."""

    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    approval_status_display = serializers.CharField(
        source='get_approval_status_display',
        read_only=True
    )

    class Meta:
        model = FacultyProfile
        fields = [
            'id', 'user_email', 'user_name',
            'employee_id', 'department', 'designation',
            'phone_number', 'joining_date', 'default_assessment_is_timed',
            'approval_status', 'approval_status_display',
            'approved_by', 'approval_date',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'approval_status', 'approved_by', 'approval_date',
            'joining_date', 'default_assessment_is_timed',
            'created_at', 'updated_at'
        ]

    def get_user_name(self, obj):
        """Get user's full name."""
        return obj.user.get_full_name()


class FacultyAssessmentPreferenceSerializer(serializers.ModelSerializer):
    """Allow faculty to update only their assessment creation preferences."""

    class Meta:
        model = FacultyProfile
        fields = ['default_assessment_is_timed']
