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
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
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


@app.route("/tasks", methods=["GET"])
def list_tasks():
    conn = get_db()
    rows = conn.execute("SELECT * FROM tasks").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/tasks", methods=["POST"])
def create_task():
    # BUG: swallowed error, silent failure — returns None instead of an error
    try:
        data = request.get_json()
        title = data["title"]
        conn = get_db()
        conn.execute("INSERT INTO tasks (title) VALUES (?)", (title,))
        conn.commit()
        conn.close()
        return jsonify({"status": "created"}), 201
    except:
        pass


@app.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
    except Exception:
        # BUG: error is caught but never logged or surfaced to caller
        return jsonify({"status": "ok"})
    finally:
        conn.close()
    return jsonify({"status": "ok"})


@app.route("/tasks/sync", methods=["POST"])
def sync_with_remote():
    # BUG: no timeout on outbound network call — can hang the whole worker
    resp = requests.get("https://example.com/api/tasks")
    remote_tasks = resp.json()
    return jsonify(remote_tasks)


@app.route("/tasks/import", methods=["POST"])
def import_tasks():
    file = request.files.get("file")
    # BUG: no None check — will throw AttributeError if 'file' missing,
    # and the exception isn't handled at all (unhandled exception -> 500 with no context)
    content = file.read().decode("utf-8")
    tasks = json.loads(content)
    conn = get_db()
    for t in tasks:
        conn.execute("INSERT INTO tasks (title) VALUES (?)", (t.get("title", ""),))
    conn.commit()
    conn.close()
    return jsonify({"imported": len(tasks)})


@app.route("/tasks/<int:task_id>/complete", methods=["POST"])
def complete_task(task_id):
    conn = get_db()
    result = conn.execute(
        "UPDATE tasks SET done = 1 WHERE id = ?", (task_id,)
    )
    conn.commit()
    conn.close()
    # BUG: doesn't check result.rowcount — silently "succeeds" even if
    # the task_id didn't exist, giving the caller false confidence
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
    except Exception as e:
        # BUG: logs to print() instead of a real logger, and still returns
        # a 200-style success message even though backup failed
        print("backup failed:", e)
        return jsonify({"status": "backed up"})


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
