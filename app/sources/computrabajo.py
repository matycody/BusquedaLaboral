"""Computrabajo Argentina: lee las páginas de resultados (HTML ya armado, 20 ofertas por página).

URL de búsqueda:  https://ar.computrabajo.com/trabajo-de-<puesto>-en-<region>?p=<pagina>
"""
import html as htmllib
import re
import time
import urllib.request
from datetime import datetime, timedelta, timezone

from ..scoring import norm

BASE = "https://ar.computrabajo.com"
UA = {"User-Agent": "Mozilla/5.0 (BusquedaLaboral personal)", "Accept-Language": "es-AR,es;q=0.9"}


def _slug(text):
    return re.sub(r"[^a-z0-9]+", "-", norm(text)).strip("-")


def _clean(fragment):
    return " ".join(htmllib.unescape(re.sub(r"<[^>]+>", " ", fragment or "")).split())


def _relative_date(text):
    t = norm(text)
    now = datetime.now(timezone.utc)
    if "ayer" in t:
        return (now - timedelta(days=1)).isoformat()
    if "hoy" in t:
        return now.isoformat()
    m = re.search(r"(\d+)\s*(minuto|hora|dia|semana|mes)", t)
    if not m:
        return None
    n, unit = int(m.group(1)), m.group(2)
    delta = {"minuto": timedelta(minutes=n), "hora": timedelta(hours=n), "dia": timedelta(days=n),
             "semana": timedelta(weeks=n), "mes": timedelta(days=30 * n)}[unit]
    return (now - delta).isoformat()


def parse_page(page_html):
    jobs = []
    for block in page_html.split('<article class="box_offer')[1:]:
        block = block.split("</article>")[0]
        m = re.search(r'<a[^>]*class="js-o-link[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', block, re.S)
        if not m:
            continue
        href, title = m.group(1).split("#")[0], _clean(m.group(2))
        comp = re.search(r"offer-grid-article-company-url[^>]*>(.*?)</a>", block, re.S)
        if comp:
            company = _clean(comp.group(1))
        else:
            p = re.search(r'<p class="dFlex[^"]*"[^>]*>(.*?)</p>', block, re.S)
            company = _clean(p.group(1)) if p else ""
        loc = re.search(r'<p class="fs16 fc_base mt5">\s*<span class="mr10">(.*?)</span>', block, re.S)
        sal = re.search(r'i_salary"></span>(.*?)</span>', block, re.S)
        date = re.search(r'<p class="fs13 fc_aux mt15">(.*?)</p>', block, re.S)
        jobs.append({
            "title": title, "company": company,
            "location": _clean(loc.group(1)) if loc else "",
            "description": f"Sueldo publicado: {_clean(sal.group(1))}." if sal else "",
            "posted": _relative_date(_clean(date.group(1))) if date else None,
            "source": "Computrabajo", "url": BASE + href if href.startswith("/") else href,
        })
    return jobs


def _get(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(3_000_000).decode(r.headers.get_content_charset() or "utf-8", "replace")


def fetch(conf, pause=1.0):
    """conf = {"enabled", "region", "queries", "max_pages"}. Devuelve (ofertas, informe)."""
    jobs, report = [], []
    region = _slug(conf.get("region") or "buenos-aires-gba")
    for q in conf.get("queries", []):
        slug, found = _slug(q), 0
        if not slug:
            continue
        note = ""
        for page in range(1, int(conf.get("max_pages", 2)) + 1):
            url = f"{BASE}/trabajo-de-{slug}-en-{region}" + (f"?p={page}" if page > 1 else "")
            try:
                got = parse_page(_get(url))
            except Exception as e:
                note = f"No se pudo leer: {e}"
                break
            jobs += got
            found += len(got)
            if len(got) < 20:
                break
            time.sleep(pause)
        time.sleep(pause)
        report.append({"busqueda": q, "encontradas": found, "nota": note})
    return jobs, report
