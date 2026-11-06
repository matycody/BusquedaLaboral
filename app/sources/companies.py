"""Revisa las páginas de empleo de las empresas de interés.

Lee el HTML de cada página y se queda con los links cuyo texto parece un puesto
(coincide con las palabras clave de tus CV). Muchas páginas de empleo cargan
con JavaScript y no muestran nada en el HTML: en ese caso se informa, no se inventa.
"""
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urljoin

from ..scoring import norm

UA = {"User-Agent": "Mozilla/5.0 (BusquedaLaboral personal)"}


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self._href, self._txt = [], None, []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._txt = []

    def handle_data(self, data):
        if self._href is not None:
            self._txt.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            text = " ".join("".join(self._txt).split())
            if text:
                self.links.append((text, self._href))
            self._href = None


def _check_one(empresa, keywords, timeout=15):
    req = urllib.request.Request(empresa["url"], headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        html = r.read(2_000_000).decode(r.headers.get_content_charset() or "utf-8", "replace")
    parser = _Links()
    parser.feed(html)
    jobs, seen = [], set()
    for text, href in parser.links:
        if not 8 <= len(text) <= 120 or href.startswith(("#", "javascript:", "mailto:")):
            continue
        n = norm(text)
        if not any(k in n for k in keywords):
            continue
        url = urljoin(empresa["url"], href)
        if url in seen:
            continue
        seen.add(url)
        jobs.append({"title": text, "company": empresa["name"], "location": "", "description": "",
                     "posted": None, "source": f"Web de {empresa['name']}", "url": url})
    return jobs


def fetch(cfg):
    keywords = {norm(k) for p in cfg["profiles"].values() for k in p["keywords"]}
    jobs, report = [], []
    for e in cfg.get("empresas", []):
        if not e.get("url"):
            continue
        try:
            found = _check_one(e, keywords)
            jobs += found
            report.append({"empresa": e["name"], "encontradas": len(found),
                           "nota": "" if found else "No se leyeron puestos en el HTML (la página probablemente carga con JavaScript). Abrila desde el link."})
        except Exception as ex:
            report.append({"empresa": e["name"], "encontradas": 0, "nota": f"No se pudo abrir: {ex}"})
    return jobs, report
