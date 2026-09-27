"""
Sample Flask API for a small task management service.
This app intentionally contains realistic error-handling bugs
for the IBM Bob Silent Failure Auditor hackathon demo.
"""
from flask import Flask, request, jsonify
import sqlite3
import requests
import json
import os

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), "tasks.db")


def get_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.OperationalError:
        app.logger.exception("Failed to connect to database at %s", DB_PATH)
        raise


def init_db():
    try:
        conn = get_db()
        conn.execute(
            """CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                done INTEGER DEFAULT 0
            )"""
        )
        conn.commit()
        conn.close()
    except sqlite3.Error:
        app.logger.exception("Failed to initialise database")
        raise

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "app": "SilentGuard — Task Manager API",
        "status": "running",
        "note": "Audited and fixed with IBM Bob 2.0",
        "endpoints": [
            "GET /tasks",
            "POST /tasks",
            "DELETE /tasks/<id>",
            "POST /tasks/<id>/complete",
            "POST /tasks/sync",
            "POST /tasks/import",
            "POST /tasks/backup"
        ]
    })

@app.route("/tasks", methods=["GET"])
def list_tasks():
    conn = get_db()
    rows = conn.execute("SELECT * FROM tasks").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/tasks", methods=["POST"])
def create_task():
    data = request.get_json(silent=True)
    if not data or "title" not in data:
        return jsonify({"error": "request body must be JSON with a 'title' field"}), 400
    title = data["title"]
    if not isinstance(title, str) or not title.strip():
        return jsonify({"error": "'title' must be a non-empty string"}), 400
    try:
        conn = get_db()
        conn.execute("INSERT INTO tasks (title) VALUES (?)", (title,))
        conn.commit()
        conn.close()
        return jsonify({"status": "created"}), 201
    except sqlite3.Error:
        app.logger.exception("create_task: database error")
        return jsonify({"error": "database error"}), 500


@app.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
    except sqlite3.Error:
        app.logger.exception("delete_task: database error for task_id=%s", task_id)
        return jsonify({"error": "database error"}), 500
    finally:
        conn.close()
    return jsonify({"status": "ok"})


@app.route("/tasks/sync", methods=["POST"])
def sync_with_remote():
    try:
        resp = requests.get("https://example.com/api/tasks", timeout=(3, 10))
        resp.raise_for_status()
        remote_tasks = resp.json()
    except requests.exceptions.Timeout:
        app.logger.exception("sync_with_remote: request timed out")
        return jsonify({"error": "remote request timed out"}), 504
    except requests.exceptions.RequestException:
        app.logger.exception("sync_with_remote: request failed")
        return jsonify({"error": "failed to reach remote API"}), 502
    return jsonify(remote_tasks)


@app.route("/tasks/import", methods=["POST"])
def import_tasks():
    file = request.files.get("file")
    if file is None:
        return jsonify({"error": "'file' field is required"}), 400
    try:
        content = file.read().decode("utf-8")
        tasks = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError):
        app.logger.exception("import_tasks: failed to parse uploaded file")
        return jsonify({"error": "file must be valid UTF-8 encoded JSON"}), 400
    valid_tasks = [t for t in tasks if isinstance(t.get("title"), str) and t["title"].strip()]
    skipped = len(tasks) - len(valid_tasks)
    try:
        conn = get_db()
        for t in valid_tasks:
            conn.execute("INSERT INTO tasks (title) VALUES (?)", (t["title"],))
        conn.commit()
        conn.close()
    except sqlite3.Error:
        app.logger.exception("import_tasks: database error")
        return jsonify({"error": "database error"}), 500
    return jsonify({"imported": len(valid_tasks), "skipped": skipped})


@app.route("/tasks/<int:task_id>/complete", methods=["POST"])
def complete_task(task_id):
    try:
        conn = get_db()
        result = conn.execute(
            "UPDATE tasks SET done = 1 WHERE id = ?", (task_id,)
        )
        conn.commit()
        conn.close()
    except sqlite3.Error:
        app.logger.exception("complete_task: database error for task_id=%s", task_id)
        return jsonify({"error": "database error"}), 500
    if result.rowcount == 0:
        return jsonify({"error": "task not found"}), 404
    return jsonify({"status": "completed"})


@app.route("/tasks/backup", methods=["POST"])
def backup_tasks():
    try:
        conn = get_db()
        rows = conn.execute("SELECT * FROM tasks").fetchall()
        conn.close()
        with open("/tmp/tasks_backup.json", "w") as f:
            json.dump([dict(r) for r in rows], f)
        return jsonify({"status": "backed up"})
    except sqlite3.Error:
        app.logger.exception("backup_tasks: database error")
        return jsonify({"error": "database error"}), 500
    except OSError:
        app.logger.exception("backup_tasks: failed to write backup file")
        return jsonify({"error": "failed to write backup file"}), 500


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
