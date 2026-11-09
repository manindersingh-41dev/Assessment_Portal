# Backend local setup

## Requirements

- Python 3.12
- PostgreSQL
- A virtual environment

## Install and configure

From the repository root:

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Create `backend/.env` from `.env.example` if you do not already have one. Set a private `SECRET_KEY`, a local PostgreSQL `DATABASE_URL` (host `localhost` for a locally installed database), email credentials, `ALLOWED_HOSTS`, and `CORS_ALLOWED_ORIGINS` for your local frontend. Never commit `.env`.

For local development, use `DEBUG=True`. For production, set `DEBUG=False`, use a strong secret, and configure the deployed host and frontend origins explicitly.

## Initialize and run

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

The API is served at `http://localhost:8000/api/` and Django Admin at `http://localhost:8000/admin/`.

## Notes

- Redis and Celery are used for background notifications and reminders. Configure the broker settings when running those workers.
- The legacy server-side code runner requires a reachable Docker daemon. A Django Docker image alone does not provide one. Browser-based evaluation does not require the API host to compile student code.
- Render's native Python service does not use the removed Docker Compose files. Configure its build/start commands and environment variables in Render when deploying.
