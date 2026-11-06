"""Servidor local sin dependencias externas (solo librería estándar)."""
import json
import mimetypes
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import config, db
from .sources import companies, demo, rss

STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except ValueError:
            return {}

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/api/jobs":
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            return self._json(db.list_jobs(
                q=q.get("q", ""), cv=q.get("cv", ""), status=q.get("status", ""),
                min_score=int(q.get("min_score") or 0), location=q.get("location", "")))
        if u.path == "/api/config":
            return self._json(config.load())
        # archivos estáticos
        rel = "index.html" if u.path in ("/", "") else u.path.lstrip("/")
        full = os.path.normpath(os.path.join(STATIC, rel))
        if not full.startswith(STATIC) or not os.path.isfile(full):
            self.send_error(404)
            return
        with open(full, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(full)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        u = urlparse(self.path)
        body = self._body()
        if u.path == "/api/demo":
            return self._json(db.upsert_jobs(demo.fetch()))
        if u.path == "/api/search":
            cfg = config.load()
            feeds = cfg.get("rss_feeds", [])
            con_url = [e for e in cfg.get("empresas", []) if e.get("url")]
            if not feeds and not con_url:
                return self._json({"agregadas": 0, "errores": [], "empresas": [],
                                   "aviso": "No hay fuentes cargadas. Agregá feeds RSS o empresas con link en Configuración."})
            jobs, errors = rss.fetch(feeds) if feeds else ([], [])
            cjobs, report = companies.fetch(cfg)
            res = db.upsert_jobs(jobs + cjobs)
            res["errores"] = errors
            res["empresas"] = report
            return self._json(res)
        if u.path == "/api/recalc":
            return self._json(db.recalc())
        if u.path == "/api/clear":
            return self._json(db.clear())
        if u.path == "/api/config":
            config.save(body)
            return self._json(db.recalc())
        if u.path == "/api/jobs":  # carga manual de una oferta
            if not body.get("title"):
                return self._json({"error": "Falta el título"}, 400)
            body.setdefault("source", "manual")
            return self._json(db.upsert_jobs([body]))
        m = re.fullmatch(r"/api/jobs/(\d+)", u.path)
        if m:
            return self._json(db.update_job(int(m.group(1)), body.get("status"), body.get("notes")))
        self.send_error(404)


def run(host="127.0.0.1", port=8000):
    config.load()
    db.conn().close()
    srv = ThreadingHTTPServer((host, port), Handler)
    print(f"Buscador de empleo listo en http://{host}:{port}  (Ctrl+C para cortar)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nChau!")
