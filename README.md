# Task Manager API (Sample App)

A small Flask API for managing tasks (create, list, complete, delete, sync, import, backup).

This is a **sample/demo project** built for the IBM Bob 2.0 Hackathon, used as the
target codebase for an automated "Silent Failure Auditor" tool built with Bob IDE.

## Setup

```bash
pip install -r requirements.txt
python app.py
```

## Endpoints

- `GET /tasks` — list all tasks
- `POST /tasks` — create a task (`{"title": "..."}`)
- `DELETE /tasks/<id>` — delete a task
- `POST /tasks/<id>/complete` — mark a task complete
- `POST /tasks/sync` — sync with a remote API
- `POST /tasks/import` — bulk import tasks from an uploaded JSON file
- `POST /tasks/backup` — back up all tasks to a local file

No real user or personal data is used or stored by this app.
