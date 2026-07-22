# Mergington High School Activities API

FastAPI application for activity registration and school announcements.

## Features

- Browse extracurricular activities with day/time filters.
- Teacher login with session validation.
- Teacher-only student registration and unregistration.
- Database-driven announcement banner.
- Teacher-only announcement management (create, edit, delete).

## Getting Started

1. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

2. Start the app:

   ```
   uvicorn src.app:app --reload
   ```

3. Open:

   - API docs: http://localhost:8000/docs
   - Alternative docs: http://localhost:8000/redoc
   - Frontend UI: http://localhost:8000/static/index.html

## API Endpoints

### Authentication

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| POST | `/auth/login?username={username}&password={password}` | Sign in as a teacher/admin |
| GET | `/auth/check-session?username={username}` | Validate current session identity |

### Activities

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| GET | `/activities` | List activities, optionally filtered by day and time |
| GET | `/activities/days` | List unique schedule days |
| POST | `/activities/{activity_name}/signup?email={student_email}&teacher_username={teacher}` | Register a student (auth required) |
| POST | `/activities/{activity_name}/unregister?email={student_email}&teacher_username={teacher}` | Remove a student (auth required) |

### Announcements

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| GET | `/announcements` | List currently active announcements for all users |
| GET | `/announcements/manage?teacher_username={teacher}` | List all announcements for management (auth required) |
| POST | `/announcements?teacher_username={teacher}` | Create announcement (auth required) |
| PUT | `/announcements/{announcement_id}?teacher_username={teacher}` | Update announcement (auth required) |
| DELETE | `/announcements/{announcement_id}?teacher_username={teacher}` | Delete announcement (auth required) |

## Announcement Rules

- `expiration_date` is required and must be in `YYYY-MM-DD` format.
- `start_date` is optional. If omitted, the announcement becomes active immediately.
- Announcements are shown publicly only when active based on start/expiration dates.

## Data Storage

MongoDB collections are initialized in `src/backend/database.py` with sample data:

- `activities`
- `teachers`
- `announcements`
