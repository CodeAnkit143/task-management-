
from datetime import date, datetime
from functools import wraps

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = "secret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

VALID_ROLES = {"admin", "member"}
VALID_TASK_STATUS = {"Pending", "In Progress", "Done"}

team_members = db.Table(
 "team_members",
 db.Column("team_id", db.Integer, db.ForeignKey("team.id"), primary_key=True),
 db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
)


class User(db.Model):
 id = db.Column(db.Integer, primary_key=True)
 name = db.Column(db.String(80), nullable=False)
 email = db.Column(db.String(120), unique=True, nullable=False)
 password = db.Column(db.String(255), nullable=False)
 role = db.Column(db.String(20), default="member", nullable=False)
 assigned_tasks = db.relationship("Task", backref="assigned_user", lazy=True)
 owned_projects = db.relationship("Project", backref="owner", lazy=True)
 teams = db.relationship("Team", secondary=team_members, back_populates="members")


class Team(db.Model):
 id = db.Column(db.Integer, primary_key=True)
 name = db.Column(db.String(120), unique=True, nullable=False)
 members = db.relationship("User", secondary=team_members, back_populates="teams")
 projects = db.relationship("Project", backref="team", lazy=True)


class Project(db.Model):
 id = db.Column(db.Integer, primary_key=True)
 name = db.Column(db.String(120), nullable=False)
 owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
 team_id = db.Column(db.Integer, db.ForeignKey("team.id"), nullable=True)
 tasks = db.relationship("Task", backref="project_obj", lazy=True)


class Task(db.Model):
 id = db.Column(db.Integer, primary_key=True)
 title = db.Column(db.String(120), nullable=False)
 status = db.Column(db.String(20), default="Pending", nullable=False)
 due_date = db.Column(db.Date, nullable=True)
 project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=True)
 assignee_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
 due = db.Column(db.String(30), nullable=True)
 project = db.Column(db.String(120), nullable=True)
 assignee = db.Column(db.String(120), nullable=True)

 @property
 def project_name(self):
  if self.project_obj:
   return self.project_obj.name
  return self.project or ""

 @property
 def assignee_name(self):
  if self.assigned_user:
   return self.assigned_user.name
  return self.assignee or ""

 @property
 def due_value(self):
  if self.due_date:
   return self.due_date.isoformat()
  return self.due or ""


def _json_error(message, code=400):
 return jsonify({"error": message}), code


def _parse_due_date(raw_due):
 if not raw_due:
  return None
 try:
  return datetime.strptime(raw_due, "%Y-%m-%d").date()
 except ValueError:
  return None


def _validate_signup_payload(name, email, password, role):
 if not name or len(name.strip()) < 2:
  return "Name must be at least 2 characters."
 if not email or "@" not in email:
  return "A valid email is required."
 if not password or len(password) < 6:
  return "Password must be at least 6 characters."
 if role not in VALID_ROLES:
  return "Role must be admin or member."
 return None


def _build_dashboard_metrics():
 tasks = Task.query.all()
 total = len(tasks)
 done = len([x for x in tasks if x.status == "Done"])
 pending = len([x for x in tasks if x.status == "Pending"])
 in_progress = len([x for x in tasks if x.status == "In Progress"])
 today = date.today()
 overdue = len(
  [x for x in tasks if x.status != "Done" and x.due_date is not None and x.due_date < today]
 )
 return {
  "tasks": tasks,
  "total": total,
  "done": done,
  "pending": pending,
  "in_progress": in_progress,
  "overdue": overdue,
 }


def login_required(fn):
 @wraps(fn)
 def wrapper(*args, **kwargs):
  if "user_id" not in session:
   if request.path.startswith("/api/"):
    return _json_error("Authentication required.", 401)
   return redirect(url_for("signin"))
  return fn(*args, **kwargs)

 return wrapper


def roles_required(*allowed_roles):
 def decorator(fn):
  @wraps(fn)
  def wrapper(*args, **kwargs):
   if session.get("role") not in allowed_roles:
    if request.path.startswith("/api/"):
     return _json_error("Forbidden: insufficient role.", 403)
    return "Forbidden: You do not have permission to access this resource.", 403
   return fn(*args, **kwargs)

  return wrapper

 return decorator


@app.route("/")
def home():
 return redirect(url_for("signin"))


@app.route("/signin", methods=["GET", "POST"])
def signin():
 if request.method == "POST":
  u = User.query.filter_by(email=request.form.get("email", "").strip()).first()
  password = request.form.get("password", "")
  if u and check_password_hash(u.password, password):
   session["user_id"] = u.id
   session["user"] = u.name
   session["role"] = u.role
   return redirect(url_for("dashboard"))
 return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
 if request.method == "POST":
  name = request.form.get("name", "").strip()
  email = request.form.get("email", "").strip().lower()
  password = request.form.get("password", "")
  role = request.form.get("role", "member")
  error = _validate_signup_payload(name, email, password, role)
  if error:
   return error, 400
  if User.query.filter_by(email=email).first():
   return "Email already exists.", 400
  u = User(
   name=name,
   email=email,
   password=generate_password_hash(password),
   role=role,
  )
  db.session.add(u)
  db.session.commit()
  return redirect(url_for("signin"))
 return render_template("signup.html")


@app.route("/logout")
def logout():
 session.clear()
 return redirect(url_for("signin"))


@app.route("/dashboard", methods=["GET", "POST"])
@login_required
@roles_required("admin", "member")
def dashboard():
 if request.method == "POST":
  title = request.form.get("title", "").strip()
  if not title:
   return "Task title is required.", 400
  due_raw = request.form.get("due", "").strip()
  due_date = _parse_due_date(due_raw)
  if due_raw and due_date is None:
   return "Invalid due date format. Use YYYY-MM-DD.", 400
  project_name = request.form.get("project", "").strip()
  assignee_name = request.form.get("assignee", "").strip()
  project = Project.query.filter_by(name=project_name).first() if project_name else None
  assignee = User.query.filter_by(name=assignee_name).first() if assignee_name else None
  t = Task(
   title=title,
   status="Pending",
   due_date=due_date,
   due=due_raw or None,
   project=project_name or None,
   assignee=assignee_name or None,
   project_id=project.id if project else None,
   assignee_id=assignee.id if assignee else None,
  )
  db.session.add(t)
  db.session.commit()
 metrics = _build_dashboard_metrics()
 projects = Project.query.order_by(Project.name.asc()).all()
 return render_template(
  "dashboard.html",
  user=session["user"],
  role=session.get("role", "member"),
  tasks=metrics["tasks"],
  projects=projects,
  total=metrics["total"],
  done=metrics["done"],
  pending=metrics["pending"],
  in_progress=metrics["in_progress"],
  overdue=metrics["overdue"],
 )


@app.route("/project", methods=["POST"])
@login_required
@roles_required("admin")
def project():
 project_name = request.form.get("name", "").strip()
 if not project_name:
  return "Project name is required.", 400
 if Project.query.filter_by(name=project_name).first():
  return "Project already exists.", 400
 p = Project(name=project_name, owner_id=session["user_id"])
 db.session.add(p)
 db.session.commit()
 return redirect(url_for("dashboard"))


@app.route("/done/<int:id>")
@login_required
@roles_required("admin")
def done(id):
 t = db.session.get(Task, id)
 if not t:
  return "Task not found.", 404
 t.status = "Done"
 db.session.commit()
 return redirect(url_for("dashboard"))


@app.route("/edit-task/<int:id>", methods=["GET", "POST"])
@login_required
@roles_required("admin")
def edit_task(id):
 task = db.session.get(Task, id)
 if not task:
  return "Task not found.", 404
 if request.method == "POST":
  title = request.form.get("title", "").strip()
  status = request.form.get("status", "Pending").strip()
  project_name = request.form.get("project", "").strip()
  assignee_name = request.form.get("assignee", "").strip()
  due_raw = request.form.get("due", "").strip()
  if not title:
   return "Task title is required.", 400
  if status not in VALID_TASK_STATUS:
   return "Invalid status. Use Pending, In Progress, or Done.", 400
  due_date = _parse_due_date(due_raw)
  if due_raw and due_date is None:
   return "Invalid due date format. Use YYYY-MM-DD.", 400
  project = Project.query.filter_by(name=project_name).first() if project_name else None
  assignee = User.query.filter_by(name=assignee_name).first() if assignee_name else None
  task.title = title
  task.status = status
  task.project = project_name or None
  task.assignee = assignee_name or None
  task.due = due_raw or None
  task.due_date = due_date
  task.project_id = project.id if project else None
  task.assignee_id = assignee.id if assignee else None
  db.session.commit()
  return redirect(url_for("dashboard"))
 return render_template("edit_task.html", task=task, statuses=sorted(VALID_TASK_STATUS))


@app.route("/delete-task/<int:id>")
@login_required
@roles_required("admin")
def delete_task(id):
 t = db.session.get(Task, id)
 if not t:
  return "Task not found.", 404
 db.session.delete(t)
 db.session.commit()
 return redirect(url_for("dashboard"))


@app.route("/api/auth/signup", methods=["POST"])
def api_signup():
 data = request.get_json(silent=True) or {}
 name = str(data.get("name", "")).strip()
 email = str(data.get("email", "")).strip().lower()
 password = str(data.get("password", ""))
 role = str(data.get("role", "member"))
 error = _validate_signup_payload(name, email, password, role)
 if error:
  return _json_error(error, 400)
 if User.query.filter_by(email=email).first():
  return _json_error("Email already exists.", 409)
 user = User(name=name, email=email, password=generate_password_hash(password), role=role)
 db.session.add(user)
 db.session.commit()
 return jsonify({"message": "User created.", "user_id": user.id}), 201


@app.route("/api/auth/login", methods=["POST"])
def api_login():
 data = request.get_json(silent=True) or {}
 email = str(data.get("email", "")).strip().lower()
 password = str(data.get("password", ""))
 user = User.query.filter_by(email=email).first()
 if not user or not check_password_hash(user.password, password):
  return _json_error("Invalid credentials.", 401)
 session["user_id"] = user.id
 session["user"] = user.name
 session["role"] = user.role
 return jsonify({"message": "Login successful.", "role": user.role}), 200


@app.route("/api/auth/logout", methods=["POST"])
@login_required
def api_logout():
 session.clear()
 return jsonify({"message": "Logged out."}), 200


@app.route("/api/teams", methods=["GET", "POST"])
@login_required
def api_teams():
 if request.method == "POST":
  if session.get("role") != "admin":
   return _json_error("Only admin can create teams.", 403)
  data = request.get_json(silent=True) or {}
  name = str(data.get("name", "")).strip()
  if not name:
   return _json_error("Team name is required.", 400)
  if Team.query.filter_by(name=name).first():
   return _json_error("Team already exists.", 409)
  team = Team(name=name)
  db.session.add(team)
  db.session.commit()
  return jsonify({"id": team.id, "name": team.name}), 201
 teams = Team.query.all()
 return jsonify([{"id": t.id, "name": t.name, "members": len(t.members)} for t in teams]), 200


@app.route("/api/teams/<int:team_id>/members", methods=["POST"])
@login_required
@roles_required("admin")
def api_add_team_member(team_id):
 team = db.session.get(Team, team_id)
 if not team:
  return _json_error("Team not found.", 404)
 data = request.get_json(silent=True) or {}
 user_id = data.get("user_id")
 if not user_id:
  return _json_error("user_id is required.", 400)
 user = db.session.get(User, user_id)
 if not user:
  return _json_error("User not found.", 404)
 if user in team.members:
  return _json_error("User already in team.", 409)
 team.members.append(user)
 db.session.commit()
 return jsonify({"message": "Member added to team."}), 200


@app.route("/api/projects", methods=["GET", "POST"])
@login_required
def api_projects():
 if request.method == "POST":
  data = request.get_json(silent=True) or {}
  name = str(data.get("name", "")).strip()
  team_id = data.get("team_id")
  if not name:
   return _json_error("Project name is required.", 400)
  if session.get("role") != "admin":
   return _json_error("Only admin can create projects.", 403)
  project = Project(name=name, owner_id=session["user_id"])
  if team_id is not None:
   team = db.session.get(Team, team_id)
   if not team:
    return _json_error("team_id is invalid.", 400)
   project.team_id = team.id
  db.session.add(project)
  db.session.commit()
  return jsonify({"id": project.id, "name": project.name, "team_id": project.team_id}), 201
 projects = Project.query.all()
 return jsonify(
  [
   {
    "id": p.id,
    "name": p.name,
    "owner_id": p.owner_id,
    "team_id": p.team_id,
    "task_count": len(p.tasks),
   }
   for p in projects
  ]
 ), 200


@app.route("/api/tasks", methods=["GET", "POST"])
@login_required
def api_tasks():
 if request.method == "POST":
  data = request.get_json(silent=True) or {}
  title = str(data.get("title", "")).strip()
  status = str(data.get("status", "Pending"))
  due_raw = str(data.get("due_date", "")).strip()
  project_id = data.get("project_id")
  assignee_id = data.get("assignee_id")
  if not title:
   return _json_error("Task title is required.", 400)
  if status not in VALID_TASK_STATUS:
   return _json_error("Invalid status. Use Pending, In Progress, or Done.", 400)
  due_date = _parse_due_date(due_raw)
  if due_raw and due_date is None:
   return _json_error("Invalid due_date format. Use YYYY-MM-DD.", 400)
  project = None
  assignee = None
  if project_id is not None:
   project = db.session.get(Project, project_id)
   if not project:
    return _json_error("project_id is invalid.", 400)
  if assignee_id is not None:
   assignee = db.session.get(User, assignee_id)
   if not assignee:
    return _json_error("assignee_id is invalid.", 400)
  task = Task(
   title=title,
   status=status,
   due_date=due_date,
   due=due_raw or None,
   project_id=project.id if project else None,
   assignee_id=assignee.id if assignee else None,
   project=project.name if project else None,
   assignee=assignee.name if assignee else None,
  )
  db.session.add(task)
  db.session.commit()
  return jsonify({"id": task.id, "title": task.title, "status": task.status}), 201
 tasks = Task.query.all()
 return jsonify(
  [
   {
    "id": t.id,
    "title": t.title,
    "status": t.status,
    "due_date": t.due_value,
    "project_id": t.project_id,
    "project_name": t.project_name,
    "assignee_id": t.assignee_id,
    "assignee_name": t.assignee_name,
    "is_overdue": bool(t.due_date and t.due_date < date.today() and t.status != "Done"),
   }
   for t in tasks
  ]
 ), 200


@app.route("/api/tasks/<int:task_id>/status", methods=["PATCH"])
@login_required
def api_task_status(task_id):
 task = db.session.get(Task, task_id)
 if not task:
  return _json_error("Task not found.", 404)
 data = request.get_json(silent=True) or {}
 status = str(data.get("status", ""))
 if status not in VALID_TASK_STATUS:
  return _json_error("Invalid status. Use Pending, In Progress, or Done.", 400)
 task.status = status
 db.session.commit()
 return jsonify({"message": "Task status updated.", "id": task.id, "status": task.status}), 200


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
@login_required
@roles_required("admin")
def api_delete_task(task_id):
 task = db.session.get(Task, task_id)
 if not task:
  return _json_error("Task not found.", 404)
 db.session.delete(task)
 db.session.commit()
 return jsonify({"message": "Task deleted.", "id": task_id}), 200


@app.route("/api/dashboard", methods=["GET"])
@login_required
def api_dashboard():
 metrics = _build_dashboard_metrics()
 return jsonify(
  {
   "total_tasks": metrics["total"],
   "done_tasks": metrics["done"],
   "pending_tasks": metrics["pending"],
   "in_progress_tasks": metrics["in_progress"],
   "overdue_tasks": metrics["overdue"],
  }
 ), 200


def init_db():
 db.create_all()
 user_cols = db.session.execute(text("PRAGMA table_info(user)")).fetchall()
 user_col_names = [c[1] for c in user_cols]
 if "role" not in user_col_names:
  db.session.execute(text("ALTER TABLE user ADD COLUMN role VARCHAR(20) DEFAULT 'member'"))
  db.session.commit()
 task_cols = db.session.execute(text("PRAGMA table_info(task)")).fetchall()
 task_col_names = [c[1] for c in task_cols]
 for col_sql, col_name in [
  ("ALTER TABLE task ADD COLUMN due_date DATE", "due_date"),
  ("ALTER TABLE task ADD COLUMN project_id INTEGER", "project_id"),
  ("ALTER TABLE task ADD COLUMN assignee_id INTEGER", "assignee_id"),
 ]:
  if col_name not in task_col_names:
   db.session.execute(text(col_sql))
   db.session.commit()
 project_cols = db.session.execute(text("PRAGMA table_info(project)")).fetchall()
 project_col_names = [c[1] for c in project_cols]
 for col_sql, col_name in [
  ("ALTER TABLE project ADD COLUMN owner_id INTEGER", "owner_id"),
  ("ALTER TABLE project ADD COLUMN team_id INTEGER", "team_id"),
 ]:
  if col_name not in project_col_names:
   db.session.execute(text(col_sql))
   db.session.commit()


if __name__ == "__main__":
 with app.app_context():
  init_db()
 app.run(debug=True)
