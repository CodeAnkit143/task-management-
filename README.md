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



