# Team Task Manager (Flask)

A simple team task manager built with Flask and SQLAlchemy.

## Features

- Authentication (`signup` / `signin`)
- Role-based access control (`admin`, `member`)
- Project management
- Team management APIs
- Task create, edit, delete, assign, and status tracking
- Dashboard metrics (`total`, `done`, `pending`, `in progress`, `overdue`)
- REST APIs for auth, projects, teams, tasks, and dashboard

## Tech Stack

- Python
- Flask
- SQLAlchemy
- SQLite

## Project Structure

- `app.py` - main Flask app, routes, models, APIs
- `templates/` - HTML templates
- `static/` - CSS and images
- `requirements.txt` - Python dependencies

## Run Locally

1. Create and activate a virtual environment:
   - Windows (PowerShell):
     - `python -m venv .venv`
     - `.venv\Scripts\Activate.ps1`
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Run the app:
   - `python app.py`
4. Open:
   - `http://127.0.0.1:5000`

## Deploy on Render (Step-by-Step)

### 1) Push project to GitHub

Render deploys from GitHub/GitLab. Make sure this project is committed and pushed.

### 2) Create a new Web Service on Render

1. Login to [Render](https://render.com)
2. Click **New +** -> **Web Service**
3. Connect your GitHub repo
4. Select this project repository

### 3) Configure service settings

Use:

- **Environment**: `Python 3`
- **Build Command**:  
  `pip install -r requirements.txt && pip install gunicorn`
- **Start Command**:  
  `gunicorn app:app`

### 4) Add environment variables (optional but recommended)

In Render service -> **Environment** add:

- `PYTHON_VERSION` = `3.11.9` (or any stable 3.11+)

### 5) Deploy

Click **Create Web Service**.  
Render will build and start your app.

### 6) Open your Render URL

Once deployment is complete, open the generated `onrender.com` URL.

## Important Note About SQLite on Render

This app currently uses SQLite (`sqlite:///data.db`).

- SQLite works for basic/demo deployments.
- On Render, filesystem can be ephemeral depending on plan and setup, so data may reset on redeploy/restart.
- For production, move to Render PostgreSQL and update DB config in `app.py`.

## API Quick Reference

- `POST /api/auth/signup`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET, POST /api/projects`
- `GET, POST /api/teams`
- `POST /api/teams/<team_id>/members`
- `GET, POST /api/tasks`
- `PATCH /api/tasks/<task_id>/status`
- `DELETE /api/tasks/<task_id>`
- `GET /api/dashboard`

## Default Roles

- `admin`: can manage projects/teams and full task actions
- `member`: can access dashboard and task operations allowed by role checks

