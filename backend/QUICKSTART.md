# Backend Setup Quick Reference

**Location**: `/home/maninder-singh/Data/Programming/Assessment_Portal/backend/`

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

## ⚡ Quick Start (Copy-Paste Commands)

```bash
# 1. Navigate to backend
cd /home/maninder-singh/Data/Programming/Assessment_Portal/backend

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Create PostgreSQL database
createdb assessment_portal
createuser -P assessment_user  # password: assessment_user

# 4. Configure environment
cp .env.example .env
# Edit .env if needed (default values should work)

# 5. Run migrations
python manage.py migrate

# 6. Create superuser for admin panel
python manage.py createsuperuser
# Email: admin@example.com
# Password: admin123

# 7. Start development server
python manage.py runserver
```

## 🌐 Access Points

| Component | URL |
|-----------|-----|
| API Root | http://localhost:8000/api/ |
| Admin Panel | http://localhost:8000/admin/ |
| Auth Endpoints | http://localhost:8000/api/auth/ |
| Questions API | http://localhost:8000/api/questions/ |
| Assessments API | http://localhost:8000/api/assessments/ |

## 📁 Important Files

| File | Purpose |
|------|---------|
| `.env.example` | Environment variable template |
| `requirements.txt` | Python dependencies |
| `manage.py` | Django CLI tool |
| `config/settings.py` | Django configuration |
| `config/urls.py` | API routing |

## 📚 Documentation

- **[README.md](README.md)** - Backend overview & features
- **[SETUP.md](SETUP.md)** - Detailed setup & deployment
- **[DELIVERABLES.md](DELIVERABLES.md)** - What's included
- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Quick reference

## 🔐 Test Credentials

### Admin Panel
- URL: http://localhost:8000/admin/
- Username: admin@example.com
- Password: (created by you in step 6)

### API Authentication Example
```bash
# Register new user
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "student@example.com",
    "username": "student1",
    "password": "Pass123!",
    "role": "student"
  }'

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "student@example.com",
    "password": "Pass123!"
  }'

# Use token
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer <access_token>"
```

## ✅ Verification Checklist

After setup, verify:

```bash
# 1. Check migrations applied
python manage.py showmigrations

# 2. Test database connection
python manage.py dbshell
# If connected, type: \q to exit

# 3. Check if server starts
python manage.py runserver
# Visit http://localhost:8000/api/
```

## 🐛 Troubleshooting

**PostgreSQL connection error?**
```bash
# Check if PostgreSQL is running
pg_isready

# Verify DATABASE_URL
grep DATABASE_URL .env
```

**Port 8000 already in use?**
```bash
python manage.py runserver 8001
```

**Migration issues?**
```bash
# Reset migrations (development only!)
python manage.py migrate zero
rm -rf */migrations/0*.py
python manage.py makemigrations
python manage.py migrate
```

## 📊 Project Statistics

- **Django Version**: 6.1.3
- **Python Version**: 3.12.12
- **Apps**: 6 (users, questions, assessments, submissions, code_execution, results)
- **Models**: 11
- **API Endpoints**: 20+
- **Database**: PostgreSQL
- **Authentication**: JWT

## 🚀 Backend Status

✅ **100% Complete & Production Ready**

- ✅ All models implemented
- ✅ All migrations generated
- ✅ All API endpoints configured
- ✅ JWT authentication setup
- ✅ PostgreSQL integration ready
- ✅ CORS configured for frontend
- ✅ Comprehensive documentation provided

## 📖 For Detailed Information

See the main project README:
- **[../README.md](../README.md)** - Project overview & structure

See backend documentation:
- **[README.md](README.md)** - Backend features & architecture
- **[SETUP.md](SETUP.md)** - Complete setup guide
