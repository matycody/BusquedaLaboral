"""Servidor local sin dependencias externas (solo librería estándar)."""
import json
import mimetypes
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import config, ctx, cvparse, db, presets, scoring, search, users
from .sources import demo

STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _token(self):
        m = re.search(r"(?:^|;\s*)sid=([\w\-]+)", self.headers.get("Cookie", ""))
        return m.group(1) if m else None

    def _begin(self, public=()):
        """Identifica al usuario de este pedido y apunta los datos a su carpeta. False si falta iniciar sesión."""
        self.user = users.user_for(self._token())
        ctx.set_dir(users.user_dir(self.user["id"]) if self.user else None)
        path = urlparse(self.path).path
        if path.startswith("/api/") and path not in public and not self.user:
            self._json({"error": "Iniciá sesión", "login": True}, 401)
            return False
        return True

    def _session_cookie(self, token, days=users.SESSION_DAYS):
        age = days * 86400 if token else 0
        return f"sid={token or ''}; HttpOnly; SameSite=Lax; Path=/; Max-Age={age}"

    def _json(self, data, code=200, headers=None):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
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
        if not self._begin(public=("/api/me",)):
            return
        if u.path == "/api/me":
            return self._json({"user": self.user, "primera": not users.has_users()})
        if u.path == "/api/cv":
            prof = re.sub(r"\W", "", parse_qs(u.query).get("profile", [""])[0])
            folder = os.path.join(ctx.data_dir(), "cvs")
            name = next((f for f in (os.listdir(folder) if os.path.isdir(folder) else []) if os.path.splitext(f)[0] == prof), None)
            if not prof or not name:
                return self._json({"error": "No hay CV cargado"}, 404)
            with open(os.path.join(folder, name), "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(name)[0] or "application/octet-stream")
            self.send_header("Content-Disposition", f'attachment; filename="{name}"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
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
            return self._json(search.progress())
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
        origin = self.headers.get("Origin")
        if origin and urlparse(origin).netloc != self.headers.get("Host"):
            return self._json({"error": "Pedido no permitido"}, 403)
        body = self._body()
        if not self._begin(public=("/api/register", "/api/login", "/api/logout")):
            return
        if u.path == "/api/register" and self.client_address[0] not in ("127.0.0.1", "::1"):
            return self._json({"error": "Las cuentas nuevas se crean desde la computadora donde corre el programa."}, 403)
        if u.path in ("/api/register", "/api/login"):
            try:
                if u.path == "/api/register":
                    user = users.register(body.get("email"), body.get("password"), body.get("nombre"))
                else:
                    user = users.authenticate(body.get("email"), body.get("password"))
            except users.AuthError as e:
                return self._json({"error": str(e)}, 400)
            token = users.new_session(user["id"])
            return self._json({"user": user}, headers={"Set-Cookie": self._session_cookie(token)})
        if u.path == "/api/logout":
            users.end_session(self._token())
            return self._json({"ok": True}, headers={"Set-Cookie": self._session_cookie("")})
        if u.path in ("/api/account/password", "/api/account/delete"):
            try:
                if u.path.endswith("password"):
                    users.change_password(self.user["id"], body.get("old"), body.get("new"), self._token())
                    return self._json({"ok": True})
                users.delete_account(self.user["id"], body.get("password"))
                return self._json({"ok": True}, headers={"Set-Cookie": self._session_cookie("")})
            except users.AuthError as e:
                return self._json({"error": str(e)}, 400)
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
            cfg = presets.apply_empresas(cfg, body.get("rubros") or [])
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
            folder = os.path.join(ctx.data_dir(), "cvs")
            os.makedirs(folder, exist_ok=True)
            for old in os.listdir(folder):  # un solo CV por perfil
                if os.path.splitext(old)[0] == prof:
                    os.remove(os.path.join(folder, old))
            with open(os.path.join(folder, prof + ext), "wb") as f:
                f.write(raw)
            cfg = config.load()
            info = {"ok": True, "leido": False, "agregadas": [], "reforzadas": [], "rubros": []}
            if prof in cfg.get("profiles", {}):
                cfg["profiles"][prof]["cv_file"] = str(body.get("filename"))[:120]
                res = cvparse.analyze(cvparse.extract_text(os.path.join(folder, prof + ext)), cfg["profiles"][prof].get("keywords", {}))
                if res:
                    cfg["profiles"][prof]["keywords"], info["agregadas"], info["reforzadas"], info["rubros"] = res
                    info["leido"] = True
                config.save(cfg)
                if info["leido"]:
                    db.recalc()
            return self._json(info)
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
            return self._json(db.update_job(int(m.group(1)), body.get("status"), body.get("notes"), body.get("outcome"), body.get("followup")))
        self.send_error(404)


def run(host="127.0.0.1", port=8000):
    for folder in users.all_dirs():
        try:
            with ctx.using(folder):
                config.load()
                db.conn().close()
                if db.clean_descriptions():
                    db.recalc()
        except Exception as e:  # la limpieza nunca debe impedir que arranque
            print("No se pudo preparar una cuenta:", e)
    stop = threading.Event()
    threading.Thread(target=search.scheduler_loop, args=(stop,), daemon=True).start()
    srv = ThreadingHTTPServer((host, port), Handler)
    print(f"Buscador de empleo listo en http://{host}:{port}  (Ctrl+C para cortar)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nChau!")
