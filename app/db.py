"""SQLite: ofertas agrupadas (un registro por oferta, varias fuentes)."""
import json
import os
import sqlite3
from datetime import datetime, timezone

from . import config
from .scoring import dedupe_key, score_job

DB_PATH = os.path.join(config.DATA_DIR, "jobs.db")


def conn():
    os.makedirs(config.DATA_DIR, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute(
        """CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE,
            title TEXT, company TEXT, location TEXT, description TEXT,
            posted TEXT, sources TEXT DEFAULT '[]',
            score INTEGER DEFAULT 0, cv TEXT, cv_scores TEXT DEFAULT '{}',
            status TEXT DEFAULT 'nueva', notes TEXT DEFAULT '',
            created TEXT
        )"""
    )
    return c


def upsert_jobs(jobs):
    """Inserta ofertas; si ya existe (mismo título+empresa+lugar) suma la fuente."""
    cfg = config.load()
    added = merged = 0
    with conn() as c:
        for j in jobs:
            key = dedupe_key(j)
            src = {"name": j.get("source", "manual"), "url": j.get("url", "")}
            row = c.execute("SELECT id, sources FROM jobs WHERE key=?", (key,)).fetchone()
            if row:
                srcs = json.loads(row["sources"])
                if not any(s["name"] == src["name"] and s["url"] == src["url"] for s in srcs):
                    srcs.append(src)
                    c.execute("UPDATE jobs SET sources=? WHERE id=?", (json.dumps(srcs), row["id"]))
                    merged += 1
                continue
            score, cv, per_cv = score_job(j, cfg)
            c.execute(
                """INSERT INTO jobs (key,title,company,location,description,posted,sources,score,cv,cv_scores,created)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (key, j.get("title", ""), j.get("company", ""), j.get("location", ""),
                 j.get("description", ""), j.get("posted"), json.dumps([src]),
                 score, cv, json.dumps(per_cv), datetime.now(timezone.utc).isoformat()),
            )
            added += 1
    return {"agregadas": added, "fuentes_nuevas_en_existentes": merged}


def recalc():
    cfg = config.load()
    n = 0
    with conn() as c:
        for r in c.execute("SELECT * FROM jobs").fetchall():
            s, cv, per = score_job(dict(r), cfg)
            c.execute("UPDATE jobs SET score=?, cv=?, cv_scores=? WHERE id=?", (s, cv, json.dumps(per), r["id"]))
            n += 1
    return {"recalculadas": n}


def list_jobs(q="", cv="", status="", min_score=0, location=""):
    sql, args = "SELECT * FROM jobs WHERE score>=?", [min_score]
    if q:
        sql += " AND (title LIKE ? OR company LIKE ? OR description LIKE ?)"
        args += [f"%{q}%"] * 3
    if cv:
        sql += " AND cv=?"
        args.append(cv)
    if status:
        sql += " AND status=?"
        args.append(status)
    if location:
        sql += " AND location LIKE ?"
        args.append(f"%{location}%")
    sql += " ORDER BY score DESC, created DESC LIMIT 500"
    with conn() as c:
        out = []
        for r in c.execute(sql, args).fetchall():
            d = dict(r)
            d["sources"] = json.loads(d["sources"])
            d["cv_scores"] = json.loads(d["cv_scores"])
            d.pop("key", None)
            out.append(d)
        return out


def update_job(job_id, status=None, notes=None):
    with conn() as c:
        if status is not None:
            c.execute("UPDATE jobs SET status=? WHERE id=?", (status, job_id))
        if notes is not None:
            c.execute("UPDATE jobs SET notes=? WHERE id=?", (notes, job_id))
    return {"ok": True}


def clear():
    with conn() as c:
        c.execute("DELETE FROM jobs")
    return {"ok": True}
