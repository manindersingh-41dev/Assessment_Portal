# Backend

Django REST API for the Geeta University Coding Assessment Portal. It handles authentication, faculty question and assessment management, student assignments, submissions, and final results.

## Local setup

Follow [`SETUP.md`](SETUP.md). The app requires PostgreSQL. Configure `DATABASE_URL`, Django secrets, allowed hosts, CORS origins, and email credentials in a local `.env` file.

The Django admin is available at `/admin/`. Its branded dashboard and styles are served by WhiteNoise; the deployment build runs `collectstatic` after migrations.

## Execution approaches

The API supports browser-reported evaluation through [`CLIENT_EXECUTION_API.md`](CLIENT_EXECUTION_API.md). A legacy Docker-backed server runner remains in the code for the alternate execution approach and transition support. The Docker deployment files formerly in this folder belonged to a legacy all-in-one Compose setup; they were removed because the selected API deployment is Render's native Python runtime.

## API references

- [`AUTH_API.md`](AUTH_API.md)
- [`QUESTIONS_API.md`](QUESTIONS_API.md)
- [`ASSESSMENTS_API.md`](ASSESSMENTS_API.md)
- [`SUBMISSIONS_API.md`](SUBMISSIONS_API.md)
- [`RESULTS_API.md`](RESULTS_API.md)

See [`TESTING.md`](TESTING.md) for the existing verification guidance.
