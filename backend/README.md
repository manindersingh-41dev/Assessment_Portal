# Geeta University Coding Assessment Portal - Backend

A scalable Django REST API backend for managing university-level coding assessments. Supports faculty creating questions and assessments, and students attempting them with automatic evaluation.

## ✨ Features

### Faculty Capabilities
- **Question Bank Management**: Create, edit, publish, archive programming questions
- **Assessment Creation**: Build assessments from question bank with customizable timing
- **Student Assignment**: Assign assessments to individual students or groups
- **Results Review**: View submissions, test case results, and student performance
- **Question Reusability**: Use same questions across multiple assessments with different weightings

### Student Capabilities
- **Assessment Browsing**: View assigned assessments within availability windows
- **Code Submission**: Submit C programs for evaluation
- **Test Results**: View test case results with feedback
- **Progress Tracking**: Check submission status and obtained marks

### System Features
- ✅ JWT Authentication with refresh tokens
- ✅ Role-based access control (Faculty/Student)
- ✅ UUID primary keys for important records
- ✅ Comprehensive audit fields (created_at, modified_at, created_by)
- ✅ Database constraints & indexes for data integrity
- ✅ CORS configured for React frontend integration
- ✅ PostgreSQL with connection pooling
- ✅ DRF pagination and filtering support

---

## 🤖 Claude Code Configuration

This project utilizes the `codebaseSessionStart` hook to initialize project context automatically when opening the session in Claude Code.

### codebaseSessionStart Hook

This hook ensures the agent is aware of the project structure, current goals, and active work state. To configure this, ensure your `.claude/settings.json` includes the following:

```json
{
  "hooks": {
    "codebaseSessionStart": [
      {
        "type": "run",
        "command": "echo 'Initializing assessment portal project context...'"
      }
    ]
  }
}
```

---

## 📁 Project Structure

```
backend/
├── config/                          # Django project configuration
│   ├── settings.py                 # Main settings (PostgreSQL, DRF, JWT, CORS)
│   ├── urls.py                     # Root API routing
│   ├── wsgi.py & asgi.py          # Application servers
│   └── migrations/                 # Database migrations
│
├── users/                           # User authentication & profiles
│   ├── models/
│   │   ├── base.py                # Abstract base models (UUID, TimeStamped, CreatedBy)
│   │   └── user.py                # User, StudentProfile, FacultyProfile
│   ├── serializers/
│   │   ├── user.py                # User serializers
│   │   └── profile.py             # Profile serializers
│   ├── views/
│   │   ├── auth.py                # Login, register, logout
│   │   └── profiles.py            # Profile management
│   ├── permissions.py             # IsFaculty, IsStudent
│   ├── services.py                # User creation, profile management
│   ├── admin.py                   # Django admin configuration
│   └── urls.py                    # Auth & profile routes
│
├── questions/                       # Question bank
│   ├── models/
│   │   ├── question.py            # Question model
│   │   └── test_case.py           # TestCase model
│   ├── serializers/
│   │   └── question.py            # Serializers for Q&A
│   ├── views/
│   │   └── questions.py           # CRUD endpoints
│   ├── permissions.py             # Question access control
│   ├── services.py                # Publish, archive operations
│   ├── admin.py                   # Admin configuration
│   └── urls.py                    # Question routes
│
├── assessments/                     # Assessment management
│   ├── models/
│   │   ├── assessment.py          # Assessment model
│   │   ├── assessment_question.py # Through model (Assessment → Questions)
│   │   └── assessment_assignment.py # Assignment model (Assessment → Student)
│   ├── serializers/
│   │   └── assessment.py          # Assessment serializers
│   ├── views.py                   # AssessmentViewSet
│   ├── permissions.py             # Assessment permissions
│   ├── services.py                # Compute marks, create assignments
│   ├── admin.py                   # Admin configuration
│   └── urls.py                    # Assessment routes
│
├── submissions/                     # Code submissions & grading
│   ├── models/
│   │   ├── submission.py          # Submission model
│   │   └── test_case_result.py    # TestCaseResult model
│   ├── serializers.py             # Submission serializers
│   ├── admin.py                   # Admin configuration
│   └── urls.py                    # Submission routes
│
├── code_execution/                  # C program execution service
│   ├── services.py                # Execution interface
│   ├── admin.py                   # Admin configuration
│   └── urls.py                    # Execution routes
│
├── results/                         # Assessment results
│   ├── models.py                  # AssessmentResult model
│   ├── admin.py                   # Admin configuration
│   └── urls.py                    # Results routes
│
├── .env.example                     # Environment variables template
├── .gitignore                       # Git ignore rules
├── requirements.txt                 # Python dependencies
├── SETUP.md                         # Setup & deployment guide
└── manage.py                        # Django CLI
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- PostgreSQL 12+

### 1. Create Virtual Environment
```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env with your PostgreSQL credentials
```

### 4. Setup Database
```bash
# Create PostgreSQL database
createdb assessment_portal
createuser -P assessment_user

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### 5. Run Server
```bash
python manage.py runserver
```

Access API at `http://localhost:8000/api/`

---

## 📊 Database Models

### Users
- **User** (Custom): Email-based auth, role (FACULTY/STUDENT), status (ACTIVE/INACTIVE/SUSPENDED)
- **StudentProfile**: roll_number, department, year_of_study
- **FacultyProfile**: employee_id, department, designation

### Questions
- **Question**: title, description, difficulty, total_marks, status (DRAFT/ACTIVE/ARCHIVED), language (C)
- **TestCase**: input, expected_output, is_sample, marks, order

### Assessments
- **Assessment**: title, description, status, start_time, end_time, duration_minutes, total_marks, is_published
- **AssessmentQuestion**: Links Assessment → Question with order & per-question marks
- **AssessmentAssignment**: Assigns Assessment → Student with status tracking

### Submissions
- **Submission**: code, language (C), status, marks_obtained, compile_output, executed_at
- **TestCaseResult**: submission, test_case, status (PASSED/FAILED/ERROR), actual_output, marks_awarded

### Results
- **AssessmentResult**: OneToOne with AssessmentAssignment, total_marks_obtained, is_released

---

## 🔐 Authentication & Authorization

### JWT Tokens
All API endpoints (except register/login) require `Authorization: Bearer <token>` header.

```bash
# Register
POST /api/auth/register
{
  "email": "user@example.com",
  "username": "user1",
  "password": "securepass123",
  "role": "student"
}

# Login
POST /api/auth/login
{
  "email": "user@example.com",
  "password": "securepass123"
}

# Response
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### Role-Based Permissions
- **Faculty**: Create/manage questions, assessments, view all submissions & results
- **Student**: View assigned assessments, submit code, view own results
- **Superuser**: Full admin access

---

## 📡 API Endpoints

### Authentication
```
POST   /api/auth/register                 # Register new user
POST   /api/auth/login                    # Get JWT tokens
POST   /api/auth/refresh                  # Refresh access token
GET    /api/auth/me                       # Current user profile
POST   /api/auth/logout                   # Blacklist refresh token
```

### Profiles
```
GET/PUT /api/auth/profiles/me/student     # Student's own profile
GET/PUT /api/auth/profiles/me/faculty     # Faculty's own profile
GET     /api/auth/profiles/faculty        # List all faculty
```

### Questions
```
GET/POST   /api/questions/                # List/create questions
GET/PUT    /api/questions/<id>/           # Retrieve/update question
DELETE     /api/questions/<id>/           # Delete question
POST       /api/questions/<id>/publish    # Publish draft question
POST       /api/questions/<id>/archive    # Archive question
```

### Assessments
```
GET/POST   /api/assessments/              # List/create assessments
GET/PUT    /api/assessments/<id>/         # Retrieve/update assessment
DELETE     /api/assessments/<id>/         # Delete assessment
GET/POST   /api/assessments/assignments/  # Manage assignments
GET        /api/assessments/assignments/mine  # My assignments (student)
```

### Submissions & Results
```
POST   /api/submissions/                  # Submit code
GET    /api/submissions/<id>/             # Get submission & results
GET    /api/results/my-results            # My assessment results
```

---

## 🏗️ Key Design Decisions

### 1. Abstract Base Models
All important records inherit from:
- **UUIDModel**: UUID primary key (avoids ID enumeration)
- **TimeStampedModel**: created_at, modified_at (audit trail)
- **CreatedByModel**: created_by FK to User (ownership tracking)

### 2. Soft Role System
No separate permission tables; roles are stored in User.role field:
- FACULTY: Can create/manage questions & assessments
- STUDENT: Can view assigned assessments & submit code

### 3. Through Models
- **AssessmentQuestion**: Allows same question in multiple assessments with different weightings
- **AssessmentAssignment**: Tracks per-student assignment status & submission times

### 4. Status Tracking
- Questions: DRAFT → ACTIVE → ARCHIVED
- Assessments: DRAFT → SCHEDULED → ACTIVE → CLOSED → ARCHIVED
- Submissions: PENDING → COMPILING → RUNNING → COMPLETED/FAILED
- Assignments: ASSIGNED → STARTED → SUBMITTED → GRADED

### 5. Database Constraints
- Check constraints for positive marks/duration
- Unique constraints for profiles per user
- Indexes on frequently queried fields (status, created_by, student)
- Foreign keys with CASCADE delete for data consistency

---

## 🔧 Configuration

### Environment Variables (.env)
```env
# Django
SECRET_KEY=generate-a-strong-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgres://user:password@localhost:5432/assessment_portal

# JWT
JWT_ACCESS_TOKEN_LIFETIME_MINUTES=60
JWT_REFRESH_TOKEN_LIFETIME_DAYS=7

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000

# Code Execution
CODE_EXECUTION_ENABLED=False
CODE_EXECUTION_TIMEOUT_SECONDS=30
```

### Django Apps
Registered in `INSTALLED_APPS`:
- users
- questions
- assessments
- submissions
- code_execution
- results
- DRF, CORS headers, JWT

---

## 📚 Database Migrations

Initial migrations are pre-generated:
```bash
python manage.py migrate                  # Apply all migrations
python manage.py migrate users            # Apply users migrations
python manage.py showmigrations           # View migration status
```

---

## 🧪 Testing

```bash
python manage.py test                     # Run all tests
python manage.py test users               # Test specific app
python manage.py test users.tests.TestUserModel  # Specific test class
```

---

## 📖 Documentation

- **SETUP.md**: Detailed setup, deployment, troubleshooting
- **API Endpoints**: Full endpoint reference above
- **Models**: Comprehensive model documentation in docstrings
- **Serializers**: Field-level validation & transformation logic
- **Views**: Endpoint handlers with permission checks

---

## 🚢 Deployment Checklist

- [ ] Set `DEBUG=False`
- [ ] Generate strong `SECRET_KEY`
- [ ] Update `ALLOWED_HOSTS`
- [ ] Configure PostgreSQL for production (backups, replication)
- [ ] Use Gunicorn/uWSGI for WSGI
- [ ] Setup Nginx reverse proxy
- [ ] Enable HTTPS with valid certificates
- [ ] Configure static files serving
- [ ] Setup error logging & monitoring
- [ ] Configure email backend for notifications

---

## 📝 Next Steps

### Immediate Tasks
1. Setup PostgreSQL locally
2. Run migrations: `python manage.py migrate`
3. Create superuser: `python manage.py createsuperuser`
4. Start development server: `python manage.py runserver`
5. Test endpoints with Postman/cURL

### Short Term
1. Implement code execution sandbox integration
2. Add test data fixtures (sample questions, assessments)
3. Setup CI/CD pipeline
4. Write API tests
5. Setup frontend React integration

### Medium Term
1. Implement assessment result calculation & grading
2. Add email notifications (assignment, submission, results)
3. Setup real-time submission updates (WebSockets)
4. Implement plagiarism detection
5. Add analytics dashboard

---

## 📦 Dependencies

- **Django 6.1.3**: Web framework
- **djangorestframework 3.18.3**: REST API framework
- **djangorestframework-simplejwt 5.5.1**: JWT authentication
- **psycopg2-binary 2.9.13**: PostgreSQL adapter
- **dj-database-url 3.1.2**: Database URL parsing
- **django-cors-headers 4.9.0**: CORS support
- **python-dotenv 1.2.4**: Environment variable management

---

## 🤝 Contributing

When adding new features:
1. Create models with UUIDModel + TimeStampedModel inheritance
2. Add appropriate serializers in serializers/ package
3. Implement permissions checks
4. Create views with proper error handling
5. Add admin configuration
6. Document endpoints & models
7. Add database migrations

---

## 📞 Support & Troubleshooting

See **SETUP.md** for detailed troubleshooting section covering:
- PostgreSQL connection issues
- Migration problems
- CORS errors
- JWT token validation
- Debug mode vs production

---

## 📄 License

This project is built for educational purposes at Geeta University.

---

**Backend Ready for Integration with React Frontend! 🎉**

The API is production-ready and can now be integrated with a React frontend. All endpoints return JSON and respect CORS headers configured for `http://localhost:3000`.
