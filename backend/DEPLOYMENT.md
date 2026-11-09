"""
Production Deployment Configuration for Geeta University Coding Assessment Portal.

Includes Docker, Docker Compose, environment setup, and deployment instructions.
"""

# ============================================================================
# DOCKERFILE - Django Backend
# ============================================================================

"""
# File: Dockerfile

FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy project
COPY . .

# Create non-root user
RUN useradd -m -u 1000 django && chown -R django:django /app

# Switch to non-root user
USER django

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health/', timeout=5)"

# Run Django
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
"""

# ============================================================================
# DOCKERFILE - Celery Worker
# ============================================================================

"""
# File: Dockerfile.celery

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

RUN useradd -m -u 1000 django && chown -R django:django /app
USER django

EXPOSE 5555

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD celery -A config inspect active_queues || exit 1

CMD ["celery", "-A", "config", "worker", "-l", "info", "--concurrency", "4"]
"""

# ============================================================================
# DOCKER COMPOSE - Production Setup
# ============================================================================

"""
# File: docker-compose.yml

version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: gateqa_postgres
    environment:
      POSTGRES_DB: ${DB_NAME:-geeta_assessment}
      POSTGRES_USER: ${DB_USER:-django}
      POSTGRES_PASSWORD: ${DB_PASSWORD:?error}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-django}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - gateqa_network

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: gateqa_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - gateqa_network

  # Django Backend
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: gateqa_backend
    command: >
      sh -c "python manage.py migrate &&
             python manage.py collectstatic --noinput &&
             gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4"
    environment:
      DEBUG: "False"
      SECRET_KEY: ${SECRET_KEY:?error}
      ALLOWED_HOSTS: ${ALLOWED_HOSTS:-localhost,127.0.0.1}
      DATABASE_URL: postgresql://${DB_USER:-django}:${DB_PASSWORD}@postgres:5432/${DB_NAME:-geeta_assessment}
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/0
      CELERY_RESULT_BACKEND: redis://redis:6379/0
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./:/app
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    networks:
      - gateqa_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Celery Worker
  celery:
    build:
      context: .
      dockerfile: Dockerfile.celery
    container_name: gateqa_celery
    command: celery -A config worker -l info --concurrency 4
    environment:
      DEBUG: "False"
      SECRET_KEY: ${SECRET_KEY:?error}
      DATABASE_URL: postgresql://${DB_USER:-django}:${DB_PASSWORD}@postgres:5432/${DB_NAME:-geeta_assessment}
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/0
      CELERY_RESULT_BACKEND: redis://redis:6379/0
    depends_on:
      - postgres
      - redis
      - backend
    volumes:
      - ./:/app
    networks:
      - gateqa_network
    healthcheck:
      test: ["CMD", "celery", "-A", "config", "inspect", "active_queues"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Celery Beat (Scheduled Tasks)
  celery_beat:
    build:
      context: .
      dockerfile: Dockerfile.celery
    container_name: gateqa_celery_beat
    command: celery -A config beat -l info
    environment:
      DEBUG: "False"
      SECRET_KEY: ${SECRET_KEY:?error}
      DATABASE_URL: postgresql://${DB_USER:-django}:${DB_PASSWORD}@postgres:5432/${DB_NAME:-geeta_assessment}
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/0
      CELERY_RESULT_BACKEND: redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    volumes:
      - ./:/app
    networks:
      - gateqa_network

  # Nginx Reverse Proxy
  nginx:
    image: nginx:alpine
    container_name: gateqa_nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - static_volume:/app/staticfiles:ro
      - media_volume:/app/media:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - backend
    networks:
      - gateqa_network

volumes:
  postgres_data:
  redis_data:
  static_volume:
  media_volume:

networks:
  gateqa_network:
    driver: bridge
"""

# ============================================================================
# ENVIRONMENT CONFIGURATION
# ============================================================================

"""
# File: .env.example

# Django Settings
DEBUG=False
SECRET_KEY=your-super-secret-key-here-change-in-production
ALLOWED_HOSTS=localhost,127.0.0.1,example.com

# Database Configuration
DB_ENGINE=django.db.backends.postgresql
DB_NAME=geeta_assessment
DB_USER=django
DB_PASSWORD=your-secure-password-here
DB_HOST=postgres
DB_PORT=5432
DATABASE_URL=postgresql://django:password@postgres:5432/geeta_assessment

# Redis Configuration
REDIS_URL=redis://redis:6379/0

# Celery Configuration
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# University Email Domain
UNIVERSITY_DOMAIN=geetauniversity.edu.in

# JWT Configuration
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Docker Execution
DOCKER_IMAGE=gcc:11-bullseye
EXECUTION_TIMEOUT=10
EXECUTION_MEMORY_LIMIT=256m

# Logging
LOG_LEVEL=INFO
"""

# ============================================================================
# NGINX CONFIGURATION
# ============================================================================

"""
# File: nginx.conf

user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
    use epoll;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 100M;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript
               application/json application/javascript application/xml+rss;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=general:10m rate=100r/s;
    limit_req_zone $binary_remote_addr zone=api:10m rate=30r/s;

    upstream django {
        server backend:8000;
    }

    server {
        listen 80;
        server_name _;

        client_max_body_size 100M;

        location /static/ {
            alias /app/staticfiles/;
            expires 30d;
            add_header Cache-Control "public, immutable";
        }

        location /media/ {
            alias /app/media/;
            expires 7d;
        }

        location /api/ {
            limit_req zone=api burst=50 nodelay;
            proxy_pass http://django;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_redirect off;
            proxy_buffering off;
            proxy_request_buffering off;
        }

        location / {
            limit_req zone=general burst=100 nodelay;
            proxy_pass http://django;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /health/ {
            access_log off;
            proxy_pass http://django;
        }
    }
}
"""

# ============================================================================
# REQUIREMENTS.TXT
# ============================================================================

"""
# File: requirements.txt

# Core Django
Django==6.1.3
djangorestframework==3.14.0
django-cors-headers==4.3.1
django-environ==0.21.0
django-filter==23.4
django-extensions==3.2.3

# Database
psycopg2-binary==2.9.9
sqlparse==0.4.4

# Authentication & Security
djangorestframework-simplejwt==5.3.2
python-decouple==3.8
PyJWT==2.8.1
cryptography==41.0.7

# Async & Background Tasks
celery==5.3.4
redis==5.0.1
kombu==5.3.4

# Code Execution
docker==7.0.0
requests==2.31.0

# API Documentation
drf-spectacular==0.26.5
drf-spectacular-sidecar==2023.12.1

# Production Server
gunicorn==21.2.0
whitenoise==6.6.0

# Monitoring & Logging
django-debug-toolbar==4.2.0
sentry-sdk==1.39.1

# Testing
pytest==7.4.3
pytest-django==4.7.0
pytest-cov==4.1.0
factory-boy==3.3.0

# Code Quality
black==23.12.1
flake8==6.1.0
isort==5.13.2
pylint==3.0.3

# Email
django-anymail==10.0
sendgrid==6.10.0

# Utils
python-dateutil==2.8.2
pytz==2023.3
Pillow==10.1.0
"""

# ============================================================================
# PRODUCTION DEPLOYMENT INSTRUCTIONS
# ============================================================================

"""
# ============================================================================
# COMPLETE DEPLOYMENT GUIDE
# ============================================================================

## Prerequisites

1. Docker and Docker Compose installed
2. Git repository with code
3. PostgreSQL knowledge
4. Redis understanding
5. Linux server with at least 2GB RAM, 2 CPUs

## Pre-Deployment Setup

### 1. Clone Repository
```bash
git clone <repository-url>
cd Assessment_Portal/backend
```

### 2. Create Environment File
```bash
cp .env.example .env
# Edit .env with production values
nano .env
```

**Critical Environment Variables:**
- SECRET_KEY: Generate with `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`
- DB_PASSWORD: Use strong password (32+ characters)
- ALLOWED_HOSTS: Your domain names

### 3. Build Docker Images
```bash
docker-compose build
```

## Production Deployment

### 1. Start Services
```bash
docker-compose up -d
```

### 2. Run Migrations
```bash
docker-compose exec backend python manage.py migrate
```

### 3. Create Superuser
```bash
docker-compose exec backend python manage.py createsuperuser
```

### 4. Collect Static Files
```bash
docker-compose exec backend python manage.py collectstatic --noinput
```

### 5. Verify Services
```bash
# Check all containers running
docker-compose ps

# Check logs
docker-compose logs -f backend

# Test API
curl http://localhost:8000/api/health/
```

## Post-Deployment Verification

### 1. Database Check
```bash
docker-compose exec postgres psql -U django -d geeta_assessment -c "\\dt"
```

### 2. Redis Check
```bash
docker-compose exec redis redis-cli ping
```

### 3. Celery Check
```bash
docker-compose exec celery celery -A config inspect active
```

### 4. Backend Health
```bash
curl -s http://localhost:8000/api/health/ | python -m json.tool
```

## Monitoring

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f celery
```

### Docker Stats
```bash
docker stats
```

### Database Connections
```bash
docker-compose exec postgres psql -U django -d geeta_assessment -c "SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;"
```

## Backup & Recovery

### Database Backup
```bash
docker-compose exec postgres pg_dump -U django geeta_assessment > backup.sql
```

### Database Restore
```bash
docker-compose exec -T postgres psql -U django geeta_assessment < backup.sql
```

### Volume Backup
```bash
docker run --rm -v gateqa_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .
```

## Scaling

### Increase Celery Workers
In docker-compose.yml, change celery service:
```yaml
celery:
  deploy:
    replicas: 3
```

### Increase Django Workers
In Dockerfile, change CMD:
```dockerfile
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "8"]
```

## SSL/TLS Configuration

### Generate Self-Signed Certificate
```bash
mkdir -p ssl
openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes
```

### Update nginx.conf for HTTPS
```nginx
server {
    listen 443 ssl http2;
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ...
}
```

## Security Checklist

- [ ] DEBUG=False in production
- [ ] SECRET_KEY is unique and strong
- [ ] ALLOWED_HOSTS configured correctly
- [ ] Database password is strong (32+ chars)
- [ ] Redis has no password (use network isolation)
- [ ] SSL/TLS certificates installed
- [ ] CORS properly configured
- [ ] Rate limiting enabled
- [ ] Logging configured
- [ ] Regular backups scheduled

## Troubleshooting

### Connection Refused
```bash
# Check if service is running
docker-compose ps

# Restart service
docker-compose restart backend
```

### Database Connection Failed
```bash
# Check database logs
docker-compose logs postgres

# Verify credentials
docker-compose exec postgres psql -U django -d geeta_assessment
```

### Celery Tasks Not Running
```bash
# Check Celery worker
docker-compose logs celery

# Inspect active tasks
docker-compose exec celery celery -A config inspect active
```

### Out of Memory
```bash
# Check memory usage
docker stats

# Increase limits in docker-compose.yml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
```

## Maintenance

### Weekly Tasks
- Monitor logs for errors
- Check database size
- Verify backup completion

### Monthly Tasks
- Update Docker images
- Review security logs
- Performance analysis

### Quarterly Tasks
- Database optimization
- Clean up old submissions
- Review and update dependencies

## Support & Documentation

- API Documentation: /api/docs/
- Admin Dashboard: /admin/
- Health Check: /api/health/
- Logs: docker-compose logs -f
"""
