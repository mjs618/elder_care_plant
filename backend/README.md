# Elder Care Platform - Backend

## Setup

```bash
cp .env.example .env
# Edit .env with your actual values

poetry install
poetry run alembic upgrade head
poetry run uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --reload
```

## API Docs
<http://localhost:8000/api/docs>
