# Task Management API (Flask)

A full-stack Task Management REST API built with **Flask**, **Flask-SQLAlchemy**,
and **Flask-JWT-Extended**. Supports user registration/login, JWT-protected
task CRUD, filtering, and pagination. Comes with a pytest test suite.

## Tech Stack

- **Framework:** Flask + Flask-RESTful-style blueprints
- **Database:** SQLite (via SQLAlchemy ORM)
- **Auth:** JWT (Flask-JWT-Extended)
- **Testing:** pytest

## Project Structure

```
task_api/
├── app.py            # App factory, blueprint registration
├── config.py          # Config classes (dev / testing)
├── models.py           # User and Task SQLAlchemy models
├── auth.py             # /api/auth routes (register, login)
├── tasks.py             # /api/tasks routes (CRUD + filtering)
├── requirements.txt
├── tests/
│   └── test_tasks.py   # pytest suite (17 tests)
└── README.md
```

## Setup

```bash
cd task_api
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Running the app

```bash
python app.py
```

The API will start at `http://127.0.0.1:5000`. A `app.db` SQLite file is
created automatically on first run.

## Running tests

```bash
pytest tests/ -v
```

All 17 tests should pass (auth: registration/login edge cases; tasks: CRUD,
filtering, ownership isolation, auth enforcement).

## API Reference

### Auth

| Method | Endpoint             | Body                                   | Description          |
|--------|-----------------------|------------------------------------------|-----------------------|
| POST   | `/api/auth/register`  | `{username, email, password}`            | Create a new user     |
| POST   | `/api/auth/login`     | `{username, password}`                   | Returns a JWT token   |

**Login response:**
```json
{
  "access_token": "eyJhbGciOi...",
  "user": {"id": 1, "username": "alice", "email": "alice@example.com", "created_at": "..."}
}
```

All `/api/tasks/*` routes below require the header:
```
Authorization: Bearer <access_token>
```

### Tasks

| Method | Endpoint            | Description                                  |
|--------|-----------------------|-------------------------------------------------|
| GET    | `/api/tasks`         | List the current user's tasks (filter/paginate)  |
| POST   | `/api/tasks`         | Create a task                                    |
| GET    | `/api/tasks/<id>`    | Get a single task                                |
| PUT    | `/api/tasks/<id>`    | Update a task                                    |
| DELETE | `/api/tasks/<id>`    | Delete a task                                    |

**Query params for `GET /api/tasks`:**
- `status` — `pending` | `in_progress` | `completed`
- `priority` — `low` | `medium` | `high`
- `search` — case-insensitive substring match on title
- `page`, `per_page` — pagination (default page=1, per_page=20, max 100)

**Task body (create/update):**
```json
{
  "title": "Write project README",
  "description": "Optional details",
  "status": "pending",
  "priority": "medium"
}
```

Each task is scoped to the authenticated user — you can never see or modify
another user's tasks (enforced at the query level, and covered by a test).

## Example curl walkthrough

```bash
# Register
curl -X POST http://127.0.0.1:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","email":"alice@example.com","password":"secret123"}'

# Login
TOKEN=$(curl -s -X POST http://127.0.0.1:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"secret123"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# Create a task
curl -X POST http://127.0.0.1:5000/api/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"title":"Buy milk","priority":"low"}'

# List tasks, filtered
curl "http://127.0.0.1:5000/api/tasks?status=pending" \
  -H "Authorization: Bearer $TOKEN"

# Update a task
curl -X PUT http://127.0.0.1:5000/api/tasks/1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"status":"completed"}'

# Delete a task
curl -X DELETE http://127.0.0.1:5000/api/tasks/1 \
  -H "Authorization: Bearer $TOKEN"
```

## Notes on production readiness

This mirrors what's expected for the project brief (entry-level portfolio
piece), but a few things worth knowing if you extend it:
- `SECRET_KEY` / `JWT_SECRET_KEY` should be set via environment variables in
  any real deployment, not left as the dev defaults in `config.py`.
- SQLite is fine for development; swap `DATABASE_URL` for Postgres/MySQL in
  production via the `SQLALCHEMY_DATABASE_URI` config.
- Add token expiry / refresh tokens if this needs to run beyond a demo.
