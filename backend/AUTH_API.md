"""
Authentication and User Management API Documentation.

Complete reference for all authentication and user management endpoints
for the Geeta University Coding Assessment Portal.
"""

# ============================================================================
# AUTHENTICATION API DOCUMENTATION
# ============================================================================

"""
BASE URL: http://localhost:8000/api/auth/

All endpoints return JSON responses with appropriate HTTP status codes.
Authentication required endpoints need JWT token in Authorization header:
    Authorization: Bearer <access_token>

============================================================================
1. USER REGISTRATION
============================================================================

### Student Registration
POST /api/auth/register/student/

Register a new student with university email.

Request Body:
{
    "email": "john.doe@geetauniversity.edu.in",
    "password": "SecurePass123",
    "password_confirm": "SecurePass123",
    "roll_number": "2024001",
    "department": "Computer Science",
    "year_of_study": 1,
    "first_name": "John",      # Optional - extracted from email if not provided
    "last_name": "Doe"         # Optional - extracted from email if not provided
}

Response (201 Created):
{
    "message": "Student registered successfully",
    "email": "john.doe@geetauniversity.edu.in",
    "next_step": "Verify your email with the OTP sent to your email address",
    "details": {
        "user_id": "uuid",
        "role": "student",
        "email_verified": false
    }
}

Errors:
- 400: Invalid email domain (must be @geetauniversity.edu.in)
- 400: Passwords do not match
- 400: Password too weak or numeric
- 400: Duplicate roll number
- 500: Email service failure

---

### Faculty Registration
POST /api/auth/register/faculty/

Register a new faculty member (pending administrator approval).

Request Body:
{
    "email": "jane.smith@geetauniversity.edu.in",
    "password": "SecurePass123",
    "password_confirm": "SecurePass123",
    "employee_id": "FAC2024001",
    "department": "Computer Science",
    "designation": "Assistant Professor",
    "first_name": "Jane",      # Optional
    "last_name": "Smith"       # Optional
}

Response (201 Created):
{
    "message": "Faculty registered successfully",
    "email": "jane.smith@geetauniversity.edu.in",
    "next_step": "Verify your email and wait for administrator approval",
    "details": {
        "user_id": "uuid",
        "role": "faculty",
        "email_verified": false,
        "approval_status": "pending"
    }
}

Notes:
- Faculty account requires administrator approval before full access
- Cannot be changed by user after registration
- Admin can approve/reject from admin panel

Errors:
- 400: Invalid email domain
- 400: Passwords do not match
- 400: Duplicate employee ID
- 500: Email service failure

============================================================================
2. EMAIL VERIFICATION
============================================================================

### Verify Email with OTP
POST /api/auth/verify-email/

Verify email using OTP received via email.

Request Body:
{
    "email": "john.doe@geetauniversity.edu.in",
    "otp": "123456"
}

Response (200 OK):
{
    "message": "Email verified successfully",
    "email": "john.doe@geetauniversity.edu.in",
    "next_step": "You can now login with your credentials"
}

Errors:
- 400: Invalid OTP
- 400: OTP expired
- 404: No user found

Notes:
- OTP expires after 10 minutes
- Valid for one-time use only
- Can only proceed with registration after email verification

---

### Resend OTP
POST /api/auth/resend-otp/

Resend OTP to email address.

Request Body:
{
    "email": "john.doe@geetauniversity.edu.in",
    "purpose": "email_verification"  # or "password_reset"
}

Response (200 OK):
{
    "message": "OTP sent successfully",
    "email": "john.doe@geetauniversity.edu.in",
    "expires_in_minutes": 10
}

Errors:
- 400: Email is required
- 400: Invalid purpose
- 404: No user found with this email
- 500: Email service failure

============================================================================
3. LOGIN & AUTHENTICATION
============================================================================

### Login
POST /api/auth/login/

Authenticate user with email and password.

Request Body:
{
    "email": "john.doe@geetauniversity.edu.in",
    "password": "SecurePass123"
}

Response (200 OK):
{
    "message": "Login successful",
    "user": {
        "id": "uuid",
        "email": "john.doe@geetauniversity.edu.in",
        "name": "John Doe",
        "role": "student"
    },
    "tokens": {
        "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
    }
}

Token Usage:
- access token: Valid for 60 minutes (configurable)
- refresh token: Valid for 7 days (configurable)
- Use access token for API calls
- Use refresh token to get new access token when expired

Errors:
- 401: Invalid email or password
- 401: Email not verified
- 401: Faculty account pending approval
- 401: Too many failed login attempts (brute-force protection)
- 401: User account is inactive

Security:
- Brute-force protection: Max 5 failed attempts in 15 minutes
- Tracks IP address and email for failed attempts
- Automatic rate limiting

---

### Logout
POST /api/auth/logout/

Logout user and invalidate tokens.

Headers:
Authorization: Bearer <access_token>

Request Body:
{
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}

Response (200 OK):
{
    "message": "Logout successful"
}

Notes:
- Invalidates refresh token (cannot get new access token)
- Access token remains valid until expiry (automatic cleanup)
- Optional: include refresh_token for immediate revocation

============================================================================
4. PASSWORD RESET
============================================================================

### Request Password Reset
POST /api/auth/password-reset-request/

Request password reset OTP.

Request Body:
{
    "email": "john.doe@geetauniversity.edu.in"
}

Response (200 OK):
{
    "message": "Password reset OTP sent to email",
    "email": "john.doe@geetauniversity.edu.in",
    "expires_in_minutes": 10
}

Errors:
- 400: Email is required
- 404: No user found
- 500: Email service failure

---

### Reset Password with OTP
POST /api/auth/password-reset/

Reset password using OTP.

Request Body:
{
    "email": "john.doe@geetauniversity.edu.in",
    "otp": "123456",
    "new_password": "NewSecurePass123",
    "new_password_confirm": "NewSecurePass123"
}

Response (200 OK):
{
    "message": "Password reset successfully",
    "next_step": "You can now login with your new password"
}

Errors:
- 400: Invalid OTP
- 400: OTP expired
- 400: Passwords do not match
- 400: New password too weak
- 404: User not found

============================================================================
5. USER PROFILE
============================================================================

### Get Current User Profile
GET /api/auth/profile/

Get authenticated user's profile.

Headers:
Authorization: Bearer <access_token>

Response (200 OK):
{
    "id": "uuid",
    "email": "john.doe@geetauniversity.edu.in",
    "full_name": "John Doe",
    "first_name": "John",
    "last_name": "Doe",
    "role": "student",
    "role_display": "Student",
    "is_email_verified": true,
    "is_faculty_approved": false,  # Only applicable for faculty
    "is_active": true,
    "created_at": "2024-11-06T10:00:00Z",
    "updated_at": "2024-11-06T10:00:00Z",
    "can_submit_code": true,
    "can_manage_assessments": false
}

Errors:
- 401: Not authenticated
- 403: Email not verified

---

### Update User Profile
PATCH /api/auth/profile/

Update current user's profile (first name, last name).

Headers:
Authorization: Bearer <access_token>

Request Body:
{
    "first_name": "Jane",
    "last_name": "Smith"
}

Response (200 OK):
{
    "message": "Profile updated successfully",
    "profile": {
        "id": "uuid",
        "email": "john.doe@geetauniversity.edu.in",
        "full_name": "Jane Smith",
        ...
    }
}

Errors:
- 401: Not authenticated
- 403: Email not verified
- 400: Invalid data

============================================================================
6. STUDENT PROFILE
============================================================================

### Get Student Profile
GET /api/auth/profile/student/

Get authenticated student's detailed profile.

Headers:
Authorization: Bearer <access_token>

Requires:
- User is student
- Email verified

Response (200 OK):
{
    "id": "uuid",
    "user_email": "john.doe@geetauniversity.edu.in",
    "user_name": "John Doe",
    "roll_number": "2024001",
    "department": "Computer Science",
    "year_of_study": 1,
    "phone_number": "+91-9876543210",
    "enrollment_date": "2024-11-06",
    "created_at": "2024-11-06T10:00:00Z",
    "updated_at": "2024-11-06T10:00:00Z"
}

Errors:
- 401: Not authenticated
- 403: Email not verified
- 403: User is not a student
- 404: Student profile not found

============================================================================
7. FACULTY PROFILE
============================================================================

### Get Faculty Profile
GET /api/auth/profile/faculty/

Get authenticated faculty's detailed profile.

Headers:
Authorization: Bearer <access_token>

Requires:
- User is faculty
- Email verified
- Account approved by administrator

Response (200 OK):
{
    "id": "uuid",
    "user_email": "jane.smith@geetauniversity.edu.in",
    "user_name": "Jane Smith",
    "employee_id": "FAC2024001",
    "department": "Computer Science",
    "designation": "Assistant Professor",
    "phone_number": "+91-9876543211",
    "joining_date": "2024-11-06",
    "approval_status": "approved",
    "approval_status_display": "Approved",
    "approved_by": "uuid",
    "approval_date": "2024-11-06T10:30:00Z",
    "created_at": "2024-11-06T10:00:00Z",
    "updated_at": "2024-11-06T10:00:00Z"
}

Errors:
- 401: Not authenticated
- 403: Email not verified
- 403: User is not faculty
- 403: Faculty account not approved
- 404: Faculty profile not found

============================================================================
8. ERROR RESPONSES
============================================================================

All errors follow this format:

{
    "error": "Error title",
    "details": "Detailed error message"
}

Or field-specific errors:

{
    "field_name": ["Error message"],
    "another_field": ["Error message"]
}

Common HTTP Status Codes:
- 200: Success
- 201: Created
- 400: Bad Request (validation error)
- 401: Unauthorized (not authenticated or failed auth)
- 403: Forbidden (authenticated but no permission)
- 404: Not Found
- 500: Internal Server Error
- 429: Too Many Requests (rate limiting)

============================================================================
9. SECURITY FEATURES
============================================================================

✓ University Email Validation
  - Only @geetauniversity.edu.in emails allowed
  - Validated at registration

✓ Email OTP Verification
  - 6-digit OTP sent via email
  - Expires after 10 minutes
  - One-time use only
  - Used for both registration and password reset

✓ JWT Authentication
  - Access token: 60 minutes (configurable)
  - Refresh token: 7 days (configurable)
  - Automatic token rotation
  - Token blacklisting on logout

✓ Brute-Force Protection
  - Max 5 failed login attempts in 15 minutes
  - Rate limiting per IP and email
  - Automatic blocking after max attempts

✓ Password Security
  - Minimum 8 characters
  - Cannot be entirely numeric
  - Bcrypt hashing (Django's default)
  - Password validators included

✓ Role-Based Access Control
  - Student role: View assessments, submit code, view results
  - Faculty role: Create questions, assessments, view submissions
  - Faculty requires administrator approval before full access

✓ Account Status Checks
  - Email must be verified before login
  - Faculty must be approved before using system
  - Inactive accounts cannot login

✓ Data Validation
  - Email format validation
  - University email domain validation
  - Password strength validation
  - Roll number uniqueness for students
  - Employee ID uniqueness for faculty

============================================================================
10. EXAMPLE WORKFLOWS
============================================================================

### Complete Student Registration & Login Workflow

1. Register:
POST /api/auth/register/student/
{
    "email": "john.doe@geetauniversity.edu.in",
    "password": "SecurePass123",
    "password_confirm": "SecurePass123",
    "roll_number": "2024001",
    "department": "Computer Science",
    "year_of_study": 1
}

2. Check email for OTP (in console or email)

3. Verify email:
POST /api/auth/verify-email/
{
    "email": "john.doe@geetauniversity.edu.in",
    "otp": "123456"
}

4. Login:
POST /api/auth/login/
{
    "email": "john.doe@geetauniversity.edu.in",
    "password": "SecurePass123"
}

5. Use access token for API calls:
GET /api/auth/profile/
Headers: Authorization: Bearer <access_token>

6. Refresh token when expired:
Use refresh token to get new access token

7. Logout:
POST /api/auth/logout/
Body: { "refresh_token": "<refresh_token>" }

---

### Faculty Registration & Approval Workflow

1. Register (same as student but with faculty endpoint)

2. Verify email (same as student)

3. Wait for administrator approval
   - Account created with approval_status: "pending"
   - Cannot login until approved

4. Administrator approves via admin panel:
   - Navigates to FacultyProfile
   - Selects faculty member
   - Clicks "Approve" action

5. Faculty can now login and use system

---

### Password Reset Workflow

1. Request reset:
POST /api/auth/password-reset-request/
{
    "email": "john.doe@geetauniversity.edu.in"
}

2. Check email for OTP

3. Reset password:
POST /api/auth/password-reset/
{
    "email": "john.doe@geetauniversity.edu.in",
    "otp": "123456",
    "new_password": "NewSecurePass123",
    "new_password_confirm": "NewSecurePass123"
}

4. Login with new password

============================================================================
"""
