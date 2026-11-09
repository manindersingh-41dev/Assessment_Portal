# Geeta University Coding Assessment Portal - Backend Setup Guide

## Overview

This is a Django-based REST API backend for a university-level coding assessment platform. It supports faculty who create and manage assessments, and students who attempt them.

**Technology Stack:**
- Python 3.12
- Django 6.1.3
- Django REST Framework 3.18.3
- PostgreSQL
- JWT Authentication (via djangorestframework-simplejwt)

---

## Project Structure

```
backend/
├── config/                    # Django project settings
│   ├── settings.py           # Main configuration (PostgreSQL, DRF, JWT, CORS)
│   ├── urls.py               # Root URL routing
│   ├── wsgi.py               # WSGI application
│   └── asgi.py               # ASGI application
├── users/                     # User management & authentication
│   ├── models/               # User, StudentProfile, FacultyProfile
│   ├── serializers/          # User serializers
│   ├── views/                # Auth, profile endpoints
│   ├── permissions.py        # Role-based permissions
│   ├── services.py           # Business logic
│   └── urls.py               # User app routes
├── questions/                 # Question bank management
│   ├── models/               # Question, TestCase
│   ├── serializers/          # Question serializers
│   ├── views/                # Question CRUD endpoints
│   ├── permissions.py        # Question access control
│   ├── services.py           # Question operations
│   └── urls.py               # Question routes
├── assessments/               # Assessment & assignment management
│   ├── models/               # Assessment, AssessmentQuestion, AssessmentAssignment
│   ├── serializers/          # Assessment serializers
│   ├── views.py              # Assessment endpoints (ViewSet)
│   ├── permissions.py        # Assessment access control
│   ├── services.py           # Assessment computation
│   └── urls.py               # Assessment routes
├── submissions/               # Student code submissions
│   ├── models/               # Submission, TestCaseResult
│   ├── serializers.py        # Submission serializers
│   └── urls.py               # Submission routes
├── code_execution/            # C program execution service (placeholder)
│   ├── services.py           # Code execution interface
│   └── urls.py               # Code execution routes
├── results/                   # Assessment results
│   ├── models.py             # AssessmentResult
│   └── urls.py               # Results routes
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore rules
├── requirements.txt          # Python dependencies
└── manage.py                 # Django management script
```

---

## Prerequisites

- **Python 3.12** (or higher)
- **PostgreSQL 12+** (running locally or remote)
- **pip** or **pip3**

---

## Installation & Setup

### 1. Create Virtual Environment

```bash
# Navigate to backend folder
cd /path/to/Assessment_Portal/backend

# Create and activate venv
python3.12 -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy `.env.example` to `.env` and update with your settings:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Django Core
SECRET_KEY=your-long-random-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# PostgreSQL
DATABASE_URL=postgres://USER:PASSWORD@localhost:5432/assessment_portal
DATABASE_SSL=False

# JWT
JWT_ACCESS_TOKEN_LIFETIME_MINUTES=60
JWT_REFRESH_TOKEN_LIFETIME_DAYS=7

# CORS (for React frontend)
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Code Execution
CODE_EXECUTION_ENABLED=False
CODE_EXECUTION_TIMEOUT_SECONDS=30
CODE_EXECUTION_MAX_MEMORY_MB=128
```

### 4. Set Up PostgreSQL Database

**Option A: Local PostgreSQL Server**

```bash
# Create database and user
createdb assessment_portal
createuser -P assessment_user  # When prompted, set password to 'password'

# Grant privileges
psql assessment_portal
# In psql:
ALTER ROLE assessment_user CREATEDB;
GRANT ALL PRIVILEGES ON DATABASE assessment_portal TO assessment_user;
\q
```

**Option B: PostgreSQL Docker Container**

```bash
docker run --name postgres-assessment \
  -e POSTGRES_DB=assessment_portal \
  -e POSTGRES_USER=assessment_user \
  -e POSTGRES_PASSWORD=password \
  -p 5432:5432 \
  -d postgres:15
```

### 5. Run Migrations

```bash
cd /path/to/Assessment_Portal/backend
source .venv/bin/activate

# Apply migrations to PostgreSQL
python manage.py migrate
```

### 6. Create Superuser (Admin)

```bash
python manage.py createsuperuser
# Follow the prompts to set email, username, password
```

### 7. Load Initial Data (Optional)

You can create initial test users/questions via management commands or the Django admin panel.

---

## Running the Backend

### Development Server

```bash
cd /path/to/Assessment_Portal/backend
source .venv/bin/activate
python manage.py runserver 0.0.0.0:8000
```

The server runs at `http://localhost:8000`.

### Access Points

- **Django Admin:** `http://localhost:8000/admin/`
- **API Root:** `http://localhost:8000/api/`
- **Auth Endpoints:** `http://localhost:8000/api/auth/`

---

## API Endpoints

### Authentication (Users App)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register a new user (faculty or student) |
| POST | `/api/auth/login` | Obtain JWT token pair (email + password) |
| POST | `/api/auth/refresh` | Refresh access token |
| GET | `/api/auth/me` | Get authenticated user's profile |
| POST | `/api/auth/logout` | Logout (blacklist refresh token) |
| GET/PUT | `/api/auth/profiles/me/student` | Student's own profile |
| GET/PUT | `/api/auth/profiles/me/faculty` | Faculty's own profile |
| GET | `/api/auth/profiles/faculty` | List all faculty (faculty only) |

### Questions (Question Bank)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/questions/` | List/create questions |
| GET/PUT/PATCH/DELETE | `/api/questions/<pk>/` | Retrieve/update/delete a question |
| POST | `/api/questions/<pk>/publish` | Publish a draft question |
| POST | `/api/questions/<pk>/archive` | Archive a question |

### Assessments

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/assessments/` | List/create assessments (faculty) |
| GET/PUT/PATCH/DELETE | `/api/assessments/<pk>/` | Retrieve/update/delete assessment |
| GET/POST | `/api/assessments/assignments/` | List/create assignments (faculty) |
| GET | `/api/assessments/assignments/mine` | My assigned assessments (student) |
| GET | `/api/assessments/assignments/<pk>/` | Get single assigned assessment (student) |

### Submissions & Results

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/submissions/` | Submit code for a question |
| GET | `/api/submissions/<pk>/` | Get submission details & test results |
| GET | `/api/results/my-results` | Get my assessment results (student) |

---

## Authentication

### JWT Tokens

All authenticated endpoints require an `Authorization` header:

```
Authorization: Bearer <access_token>
```

### Example Flow

1. **Register:**
   ```bash
   curl -X POST http://localhost:8000/api/auth/register \
     -H "Content-Type: application/json" \
     -d '{
       "email": "student@example.com",
       "username": "student1",
       "password": "securepassword123",
       "role": "student",
       "first_name": "John",
       "last_name": "Doe"
     }'
   ```

2. **Login:**
   ```bash
   curl -X POST http://localhost:8000/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{
       "email": "student@example.com",
       "password": "securepassword123"
     }'
   ```

   Response:
   ```json
   {
     "access": "<access_token>",
     "refresh": "<refresh_token>"
   }
   ```

3. **Use Token:**
   ```bash
   curl -X GET http://localhost:8000/api/auth/me \
     -H "Authorization: Bearer <access_token>"
   ```

---

## Database Models

### Users App

- **User**: Custom user model with email authentication, role-based (FACULTY/STUDENT)
- **StudentProfile**: Extends user with roll_number, department, year_of_study
- **FacultyProfile**: Extends user with employee_id, department, designation

### Questions App

- **Question**: Programming problem (C language), created by faculty
- **TestCase**: Input/output test case for a question (sample or hidden)

### Assessments App

- **Assessment**: Collection of questions with time window, created by faculty
- **AssessmentQuestion**: Links questions to assessments with marks weighting
- **AssessmentAssignment**: Assigns an assessment to a student

### Submissions App

- **Submission**: Student's code submission for a question
- **TestCaseResult**: Result of running submission against a test case

### Results App

- **AssessmentResult**: Summary of student's performance on an assessment

---

## Role-Based Access Control

### Faculty Permissions
- ✅ Create, view, update, delete questions
- ✅ Publish/archive questions
- ✅ Create assessments
- ✅ Add questions to assessments
- ✅ Assign assessments to students
- ✅ View all submissions & results

### Student Permissions
- ✅ View assigned (published) assessments
- ✅ Attempt assessments within time window
- ✅ Submit C programs
- ✅ View own test case results (when graded)
- ❌ Cannot create/modify questions
- ❌ Cannot create/modify assessments

---

## Code Execution (Placeholder)

The `code_execution` app provides a service interface for executing C programs. Currently, it's a placeholder; integration with a sandbox/container runtime (Docker, AWS Lambda, etc.) would be implemented here.

---

## Troubleshooting

### PostgreSQL Connection Refused
- Ensure PostgreSQL is running: `pg_isready`
- Check `DATABASE_URL` in `.env` is correct
- Verify username/password/database name

### Django Migrations Issues
```bash
# Check migration status
python manage.py showmigrations

# Reset all migrations (development only!)
python manage.py migrate zero
rm -rf */migrations/0*.py
python manage.py makemigrations
python manage.py migrate
```

### CORS Issues with React Frontend
- Update `CORS_ALLOWED_ORIGINS` in `.env` with React app's origin
- Ensure `CORS_ALLOW_CREDENTIALS=True` in settings

### Secret Key Warning
- Generate a new `SECRET_KEY` in settings.py before production:
  ```python
  from django.core.management.utils import get_random_secret_key
  print(get_random_secret_key())
  ```

---

## Production Deployment

### Before Deploying:

1. Set `DEBUG=False` in `.env`
2. Generate a strong `SECRET_KEY`
3. Update `ALLOWED_HOSTS` to your domain
4. Use a production WSGI server (Gunicorn, uWSGI)
5. Set up proper database backups
6. Configure static files & media serving
7. Use HTTPS with valid certificates
8. Set up environment-specific settings

### Example with Gunicorn:

```bash
pip install gunicorn
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

---

## Testing

Run tests:
```bash
python manage.py test
```

Run tests for a specific app:
```bash
python manage.py test users
python manage.py test questions
```

---

## Admin Panel

Access at `http://localhost:8000/admin/` with your superuser credentials.

From here you can:
- Manage users, students, faculty
- Create/edit questions and test cases
- Create assessments and assignments
- View submissions and results

---

## Additional Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [SimpleJWT Authentication](https://django-rest-framework-simplejwt.readthedocs.io/)
- [CORS Headers](https://github.com/adamchainz/django-cors-headers)

---

## Support

For issues or questions:
1. Check the logs: `python manage.py runserver` output
2. Enable debug mode: `DEBUG=True` in `.env`
3. Check Django admin for data inconsistencies
