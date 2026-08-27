# Database

PostgreSQL is defined in `docker-compose.yml`, configured through `DATABASE_URL`, and managed with Alembic migrations under `backend/alembic`. Monetary columns store integer minor units (paise for INR).

From `backend`, run `alembic upgrade head` to create/update the schema and `python -m app.seed` to safely replace the deterministic demo merchant dataset.
