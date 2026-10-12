from __future__ import annotations
import json
import os
import sqlite3
import time
import uuid

SCHEMA = """
CREATE TABLE IF NOT EXISTS analyses (
  id TEXT PRIMARY KEY,
  input TEXT NOT NULL,
  result_json TEXT NOT NULL,
  retrieval_mode TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS actions (
  id TEXT PRIMARY KEY,
  analysis_id TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  department TEXT NOT NULL,
  owner TEXT NOT NULL,
  priority TEXT NOT NULL,
  evidence_json TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft',
  idempotency_key TEXT NOT NULL UNIQUE,
  approval_note TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS activity (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kind TEXT NOT NULL,
  message TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS local_memory (
  id TEXT PRIMARY KEY,
  text TEXT NOT NULL,
  created_at TEXT NOT NULL
);
"""

def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

class Store:
    def __init__(self, path: str):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.path = path
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    def log(self, kind: str, message: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO activity (kind, message, created_at) VALUES (?, ?, ?)",
                (kind, message, _now()),
            )

    def save_analysis(self, analysis_id: str, inp: str, result: dict, mode: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO analyses (id, input, result_json, retrieval_mode, created_at) VALUES (?, ?, ?, ?, ?)",
                (analysis_id, inp, json.dumps(result), mode, _now()),
            )
            conn.execute(
                "INSERT INTO activity (kind, message, created_at) VALUES (?, ?, ?)",
                ("analysis", f"Analysis {analysis_id} completed in {mode} mode", _now()),
            )

    def get_analysis(self, analysis_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
            if not row:
                return None
            return json.loads(row["result_json"])

    def upsert_action(self, action: dict) -> dict:
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT * FROM actions WHERE idempotency_key = ?", (action["idempotency_key"],)
            ).fetchone()
            if existing:
                return dict(existing)
            now = _now()
            conn.execute(
                """INSERT INTO actions
                (id, analysis_id, title, description, department, owner, priority, evidence_json, status, idempotency_key, approval_note, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    action["id"], action["analysis_id"], action["title"], action["description"],
                    action["department"], action.get("owner", ""), action.get("priority", "Medium"),
                    json.dumps(action.get("evidence", [])), action.get("status", "draft"),
                    action["idempotency_key"], action.get("approval_note", ""), now, now,
                ),
            )
            conn.execute(
                "INSERT INTO activity (kind, message, created_at) VALUES (?, ?, ?)",
                ("action_created", f"Draft created: {action['title']} [{action['department']}]", _now()),
            )
            row = conn.execute("SELECT * FROM actions WHERE id = ?", (action["id"],)).fetchone()
            return dict(row)

    def list_actions(self, status: str | None = None) -> list[dict]:
        with self._connect() as conn:
            if status:
                rows = conn.execute("SELECT * FROM actions WHERE status = ? ORDER BY created_at DESC", (status,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM actions ORDER BY created_at DESC").fetchall()
            out = []
            for r in rows:
                d = dict(r)
                d["evidence"] = json.loads(d.pop("evidence_json") or "[]")
                out.append(d)
            return out

    def set_action_status(self, action_id: str, status: str, note: str = "") -> dict | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM actions WHERE id = ?", (action_id,)).fetchone()
            if not row:
                return None
            d = dict(row)
            if d["status"] != "draft":
                return {**d, "evidence": json.loads(d["evidence_json"] or "[]")}
            conn.execute(
                "UPDATE actions SET status = ?, approval_note = ?, updated_at = ? WHERE id = ?",
                (status, note, _now(), action_id),
            )
            conn.execute(
                "INSERT INTO activity (kind, message, created_at) VALUES (?, ?, ?)",
                (f"action_{status}", f"Action {action_id} {status}: {d['title']}", _now()),
            )
            row2 = conn.execute("SELECT * FROM actions WHERE id = ?", (action_id,)).fetchone()
            d2 = dict(row2)
            d2["evidence"] = json.loads(d2.pop("evidence_json") or "[]")
            return d2

    def add_memory(self, text: str) -> str:
        mid = f"mem_{uuid.uuid4().hex[:10]}"
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO local_memory (id, text, created_at) VALUES (?, ?, ?)",
                (mid, text, _now()),
            )
            conn.execute(
                "INSERT INTO activity (kind, message, created_at) VALUES (?, ?, ?)",
                ("memory", f"Approval memory recorded: {text[:120]}", _now()),
            )
        return mid

    def list_memory(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM local_memory ORDER BY created_at DESC LIMIT 50").fetchall()
            return [dict(r) for r in rows]

    def list_activity(self, limit: int = 100) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM activity ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]
