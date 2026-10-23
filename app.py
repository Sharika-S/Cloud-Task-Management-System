from flask import Flask, request, redirect, render_template_string
import sqlite3
from pathlib import Path
from datetime import date

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "tasks.db"

PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Cloud Task Manager</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: Arial, sans-serif;
            background: #eef2ff;
            color: #222;
            margin: 0;
            padding: 24px;
        }
        .container {
            max-width: 1000px;
            margin: auto;
            background: white;
            padding: 25px;
            border-radius: 14px;
            box-shadow: 0 4px 18px #d7dced;
        }
        h1 { text-align: center; color: #354bb5; }
        .subtitle { text-align: center; color: #666; }
        .stats {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin: 25px 0;
        }
        .stat {
            background: #eef1ff;
            padding: 18px;
            border-radius: 10px;
            text-align: center;
        }
        .stat strong { display: block; font-size: 25px; color: #354bb5; }
        .formbox { background: #f7f8ff; padding: 18px; border-radius: 10px; }
        input, select {
            width: 100%;
            padding: 11px;
            margin: 7px 0 13px;
            border: 1px solid #ccc;
            border-radius: 6px;
        }
        button, .editlink {
            background: #4058bd;
            color: white;
            padding: 9px 12px;
            border: 0;
            border-radius: 6px;
            cursor: pointer;
            text-decoration: none;
        }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { text-align: left; padding: 12px 8px; border-bottom: 1px solid #ddd; }
        th { background: #e8ecff; }
        .done { color: #168447; font-weight: bold; }
        .pending { color: #b36a00; font-weight: bold; }
        .delete { background: #c0392b; }
        .actions form { display: inline-block; margin: 3px 0; }
        .actions button { padding: 7px 9px; }
        .small { font-size: 13px; color: #666; }
        @media(max-width: 650px) {
            body { padding: 8px; }
            .container { padding: 12px; }
            th, td { font-size: 12px; padding: 7px 4px; }
            .stats { gap: 5px; }
            .stat { padding: 10px 4px; }
        }
    </style>
</head>
<body>
<div class="container">
    <h1>☁️ Cloud Task Manager</h1>
    <p class="subtitle">Organize your tasks. Track your progress. Reach your goals.</p>

    <div class="stats">
        <div class="stat"><strong>{{ total }}</strong>Total Tasks</div>
        <div class="stat"><strong>{{ pending }}</strong>Pending</div>
        <div class="stat"><strong>{{ completed }}</strong>Completed</div>
    </div>

    <div class="formbox">
        <h3>{{ "Edit Task" if editing else "Add a New Task" }}</h3>
        <form method="POST" action="{{ '/edit/' ~ editing[0] if editing else '/add' }}">
            <label>Task Name</label>
            <input name="title" required maxlength="120"
                   placeholder="Enter task name"
                   value="{{ editing[1] if editing else '' }}">

            <label>Due Date</label>
            <input type="date" name="due_date"
                   value="{{ editing[2] if editing else '' }}">

            <label>Priority</label>
            <select name="priority">
                {% for p in ['Low', 'Medium', 'High'] %}
                <option value="{{ p }}"
                {% if editing and editing[3] == p %}selected
                {% elif not editing and p == 'Medium' %}selected{% endif %}>
                    {{ p }}
                </option>
                {% endfor %}
            </select>

            <button type="submit">{{ "Save Changes" if editing else "Add Task" }}</button>
            {% if editing %}
            <a class="editlink" href="/">Cancel</a>
            {% endif %}
        </form>
    </div>

    <h3>Your Tasks</h3>
    <p class="small">Edit tasks, update their status, or delete them.</p>
    <table>
        <tr>
            <th>Task</th><th>Due Date</th><th>Priority</th>
            <th>Status</th><th>Actions</th>
        </tr>
        {% for task in tasks %}
        <tr>
            <td>{{ task[1] }}</td>
            <td>{{ task[2] if task[2] else 'Not set' }}</td>
            <td>{{ task[3] }}</td>
            <td class="{{ 'done' if task[4] == 'Completed' else 'pending' }}">
                {{ task[4] }}
            </td>
            <td class="actions">
                <a class="editlink" href="/edit/{{ task[0] }}">Edit</a>
                <form method="POST" action="/status/{{ task[0] }}">
                    <button type="submit">
                        {{ 'Reopen' if task[4] == 'Completed' else 'Complete' }}
                    </button>
                </form>
                <form method="POST" action="/delete/{{ task[0] }}"
                      onsubmit="return confirm('Delete this task?')">
                    <button class="delete" type="submit">Delete</button>
                </form>
            </td>
        </tr>
        {% else %}
        <tr><td colspan="5">No tasks yet. Add your first task above!</td></tr>
        {% endfor %}
    </table>
</div>
</body>
</html>
"""

def get_connection():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            due_date TEXT DEFAULT '',
            priority TEXT NOT NULL DEFAULT 'Medium',
            status TEXT NOT NULL DEFAULT 'Pending'
        )
    """)
    return con

@app.route("/")
def home():
    editing_id = request.args.get("editing", type=int)
    with get_connection() as con:
        tasks = con.execute(
            "SELECT id, title, due_date, priority, status FROM tasks ORDER BY id DESC"
        ).fetchall()
        editing = None
        if editing_id:
            editing = con.execute(
                "SELECT id, title, due_date, priority FROM tasks WHERE id = ?",
                (editing_id,)
            ).fetchone()

    total = len(tasks)
    completed = sum(1 for task in tasks if task[4] == "Completed")
    pending = total - completed
    return render_template_string(
        PAGE, tasks=tasks, total=total, pending=pending,
        completed=completed, editing=editing
    )

@app.route("/add", methods=["POST"])
def add_task():
    title = request.form.get("title", "").strip()
    due_date = request.form.get("due_date", "")
    priority = request.form.get("priority", "Medium")
    if title and priority in ("Low", "Medium", "High"):
        with get_connection() as con:
            con.execute(
                "INSERT INTO tasks (title, due_date, priority) VALUES (?, ?, ?)",
                (title, due_date, priority)
            )
    return redirect("/")

@app.route("/edit/<int:task_id>", methods=["GET", "POST"])
def edit_task(task_id):
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        due_date = request.form.get("due_date", "")
        priority = request.form.get("priority", "Medium")
        if title and priority in ("Low", "Medium", "High"):
            with get_connection() as con:
                con.execute(
                    "UPDATE tasks SET title=?, due_date=?, priority=? WHERE id=?",
                    (title, due_date, priority, task_id)
                )
        return redirect("/")
    return redirect("/?editing=" + str(task_id))

@app.route("/status/<int:task_id>", methods=["POST"])
def update_status(task_id):
    with get_connection() as con:
        con.execute("""
            UPDATE tasks
            SET status = CASE
                WHEN status = 'Completed' THEN 'Pending'
                ELSE 'Completed'
            END
            WHERE id = ?
        """, (task_id,))
    return redirect("/")

@app.route("/delete/<int:task_id>", methods=["POST"])
def delete_task(task_id):
    with get_connection() as con:
        con.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    return redirect("/")

if __name__ == "__main__":
    with get_connection():
        pass
    app.run(debug=True, port=5008)
