"""Servidor local sin dependencias externas (solo librería estándar)."""
import json
import mimetypes
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import config, db, presets, scoring, search
from .sources import demo

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
        if u.path == "/api/export":
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            status = q.get("status", "aplicada")
            if status not in ("aplicada", "interesa", "descartada", "nueva"):
                status = "aplicada"
            body = db.export_csv(status).encode("utf-8-sig")  # con BOM para que Excel respete los acentos
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="ofertas-{status}.csv"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if u.path == "/api/explain":
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            job = db.get_job(int(q.get("id") or 0))
            if not job:
                return self._json({"items": [], "total": 0}, 404)
            return self._json(scoring.explain(job, config.load()))
        if u.path == "/api/config":
            return self._json(config.load())
        if u.path == "/api/search/progress":
            return self._json(search.PROGRESS)
        if u.path == "/api/presets":
            return self._json(presets.listing())
        if u.path == "/api/status":
            st = search.load_state()
            return self._json({"last_search": st.get("last_search"), "last_added": st.get("last_added", 0)})
        if u.path == "/api/jooble/status":
            return self._json({"key_set": bool(config.get_secret("jooble_key", "JOOBLE_API_KEY"))})
        if u.path == "/api/gmail/status":
            return self._json({"password_set": bool(config.get_secret("gmail_password", "GMAIL_APP_PASSWORD"))})
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
            res = search.run_search()
            return self._json(res if res is not None else {"agregadas": 0, "aviso": "Ya hay una búsqueda en curso. Esperá a que termine."})
        if u.path == "/api/jooble/key":
            config.set_secret("jooble_key", "".join(str(body.get("key", "")).split()))
            return self._json({"key_set": bool(config.get_secret("jooble_key"))})
        if u.path == "/api/gmail/password":
            config.set_secret("gmail_password", "".join(str(body.get("password", "")).split()))
            return self._json({"password_set": bool(config.get_secret("gmail_password"))})
        if u.path == "/api/recalc":
            return self._json(db.recalc())
        if u.path == "/api/clear":
            return self._json(db.clear())
        if u.path == "/api/setup":
            base = config.load()
            had = base.get("setup_done")
            base.pop("setup_done", None)
            cfg = presets.apply(base, body.get("rubros") or [], body.get("extra") or [])
            if not cfg.get("setup_done"):
                if had:
                    cfg["setup_done"] = True  # solo cambió los datos personales
                else:
                    return self._json({"error": "Elegí al menos un rubro o escribí un puesto"}, 400)
            cfg = presets.apply_perfil(cfg, body.get("perfil"))
            config.save(cfg)
            return self._json(db.recalc())
        if u.path == "/api/cv":
            import base64
            prof = re.sub(r"\W", "", str(body.get("profile", "")))
            ext = os.path.splitext(str(body.get("filename", "")))[1].lower()
            if not prof or ext not in (".pdf", ".doc", ".docx", ".odt", ".txt"):
                return self._json({"error": "Subí un CV en PDF, Word o texto"}, 400)
            try:
                raw = base64.b64decode(body.get("data", ""), validate=False)
            except Exception:
                return self._json({"error": "Archivo ilegible"}, 400)
            if not raw or len(raw) > 5 * 1024 * 1024:
                return self._json({"error": "El CV debe pesar hasta 5 MB"}, 400)
            os.makedirs(os.path.join(config.DATA_DIR, "cvs"), exist_ok=True)
            with open(os.path.join(config.DATA_DIR, "cvs", prof + ext), "wb") as f:
                f.write(raw)
            cfg = config.load()
            if prof in cfg.get("profiles", {}):
                cfg["profiles"][prof]["cv_file"] = str(body.get("filename"))[:120]
                config.save(cfg)
            return self._json({"ok": True})
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
    stop = threading.Event()
    threading.Thread(target=search.scheduler_loop, args=(stop,), daemon=True).start()
    srv = ThreadingHTTPServer((host, port), Handler)
    print(f"Buscador de empleo listo en http://{host}:{port}  (Ctrl+C para cortar)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nChau!")
