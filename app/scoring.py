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

    rec_bonus = experience_adjust(title, desc)
    posted = job.get("posted")
    if posted:
        try:
            d = datetime.fromisoformat(posted)
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            days = (datetime.now(timezone.utc) - d).days
            rec_bonus += 8 if days <= 3 else 4 if days <= 10 else 0 if days <= 21 else -8 if days <= 45 else -15
        except ValueError:
            pass

    comp = norm(job.get("company"))
    comp_bonus = 0
    if comp and any(norm(e.get("name")) and norm(e["name"]) in comp for e in cfg.get("empresas", [])):
        comp_bonus = cfg.get("company_bonus", 10)

    score = max(0, min(100, round(base * 0.82 + loc_bonus + rec_bonus + comp_bonus + pen)))
    return score, best_cv, {k: round(v) for k, v in per_cv.items()}


_YEARS = re.compile(r"(\d+)\s*\+?\s*anos?[^.\n]{0,30}experiencia|experiencia[^.\n]{0,40}?(\d+)\s*\+?\s*anos?")
_SENIOR_TITLE = re.compile(r"\b(sr|ssr|sr\.|semi ?sr|senior|semi ?senior|lider|gerente|jefe|coordinador|encargado)\b")
_NO_EXP = ("sin experiencia", "no requiere experiencia", "no es necesaria experiencia", "primer empleo", "primera experiencia")


def experience_adjust(title, desc):
    """Penaliza lo que pide años de experiencia y premia lo abierto a primer empleo."""
    adj = 0
    if _SENIOR_TITLE.search(title):
        adj -= 12
    years = [int(g) for m in _YEARS.finditer(desc) for g in m.groups() if g]
    years = [y for y in years if 1 <= y <= 20]
    if years:
        n = max(years)
        adj -= 3 if n == 1 else min(24, 6 * n)
    elif any(k in desc for k in _NO_EXP) or any(k in title for k in _NO_EXP):
        adj += 6
    if re.search(r"\b(trainee|pasante|junior|jr|ayudante|aprendiz|practicante)\b", title):
        adj += 4
    return adj


def dedupe_key(job):
    return norm(f"{job.get('title')}|{job.get('company')}|{job.get('location')}")
