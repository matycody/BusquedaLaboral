"""Puntaje 0-100 y recomendación de CV."""
import re
import unicodedata
from datetime import datetime, timezone


def norm(text):
    text = unicodedata.normalize("NFD", text or "").lower()
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", text).strip()


def _profile_score(profile, title, desc):
    kws = profile["keywords"]
    total_possible = sum(kws.values()) or 1
    raw = 0
    for kw, w in kws.items():
        k = norm(kw)
        if k in title:
            raw += w * 2
        elif k in desc:
            raw += w
    # Con ~45% del total posible ya es una coincidencia excelente.
    return min(100.0, raw / (total_possible * 0.45) * 100)


def score_job(job, cfg):
    title = norm(job.get("title"))
    desc = norm(job.get("description"))
    loc = norm(job.get("location"))

    per_cv = {name: _profile_score(p, title, desc) for name, p in cfg["profiles"].items()}
    best_cv = max(per_cv, key=per_cv.get)
    base = per_cv[best_cv]

    pen = 0
    for word, p in cfg.get("penalize", {}).items():
        if norm(word) in title or norm(word) in desc:
            pen += p

    loc_bonus = 0
    oks = [norm(x) for x in cfg.get("locations_ok", [])]
    if any(o and o in loc for o in oks) or "remoto" in loc or "remoto" in desc:
        loc_bonus = 10

    rec_bonus = 0
    posted = job.get("posted")
    if posted:
        try:
            d = datetime.fromisoformat(posted)
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            days = (datetime.now(timezone.utc) - d).days
            rec_bonus = 8 if days <= 3 else 4 if days <= 10 else 0
        except ValueError:
            pass

    comp = norm(job.get("company"))
    comp_bonus = 0
    if comp and any(norm(e.get("name")) and norm(e["name"]) in comp for e in cfg.get("empresas", [])):
        comp_bonus = cfg.get("company_bonus", 10)

    score = max(0, min(100, round(base * 0.82 + loc_bonus + rec_bonus + comp_bonus + pen)))
    return score, best_cv, {k: round(v) for k, v in per_cv.items()}


def dedupe_key(job):
    return norm(f"{job.get('title')}|{job.get('company')}|{job.get('location')}")
