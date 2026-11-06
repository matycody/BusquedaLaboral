"""Ejecuta una búsqueda completa en todas las fuentes activas."""
import json
import os
import threading
import time

from . import config, db
from .sources import bumeran, companies, computrabajo, gmail, rss, zonajobs

STATE_PATH = os.path.join(config.DATA_DIR, "state.json")
_lock = threading.Lock()


def load_state():
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save_state(**kw):
    st = load_state()
    st.update(kw)
    os.makedirs(config.DATA_DIR, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(st, f)


def enrich_computrabajo(conf, pause=1.0):
    """Lee el aviso completo de las ofertas de Computrabajo con buen puntaje y las vuelve a puntuar."""
    if not conf.get("enabled"):
        return {"leidos": 0, "fallos": 0}
    ok = bad = 0
    for item in db.pending_descriptions("Computrabajo", limit=int(conf.get("max_details", 25))):
        try:
            text = computrabajo.fetch_detail(item["url"])
            if text:
                db.set_description(item["id"], text)
                ok += 1
        except Exception:
            bad += 1
            if bad >= 3:  # si falla seguido, mejor frenar que insistir
                break
        time.sleep(pause)
    return {"leidos": ok, "fallos": bad}


def run_search():
    """Devuelve el resultado, o None si ya hay otra búsqueda corriendo."""
    if not _lock.acquire(blocking=False):
        return None
    try:
        cfg = config.load()
        feeds = cfg.get("rss_feeds", [])
        con_url = [e for e in cfg.get("empresas", []) if e.get("url")]
        portales = cfg.get("portales", {})
        activos = [(name, mod) for name, mod in (("Computrabajo", computrabajo), ("Bumeran", bumeran), ("ZonaJobs", zonajobs))
                   if portales.get(name.lower(), {}).get("enabled") and portales.get(name.lower(), {}).get("queries")]
        gm = cfg.get("gmail", {})
        gm_pass = config.get_secret("gmail_password", "GMAIL_APP_PASSWORD")
        use_gm = bool(gm.get("enabled") and gm.get("email") and gm_pass)
        if not feeds and not con_url and not activos and not use_gm:
            return {"agregadas": 0, "errores": [], "empresas": [], "portales": [], "gmail": [],
                    "aviso": "No hay fuentes cargadas. Activá un portal, agregá feeds RSS o empresas con link en Configuración."}

        jobs, errors = rss.fetch(feeds) if feeds else ([], [])
        cjobs, report = companies.fetch(cfg)
        pjobs, preport = [], []
        for name, mod in activos:
            got, rep = mod.fetch(portales[name.lower()])
            pjobs += got
            preport += [{**r, "portal": name} for r in rep]
        gjobs, greport = [], []
        if use_gm:
            try:
                gjobs, greport = gmail.fetch(gm, gm_pass)
            except Exception as e:
                greport = [{"correo": "", "encontradas": 0, "nota": f"No se pudo leer Gmail: {e}"}]
        res = db.upsert_jobs(jobs + cjobs + pjobs + gjobs)
        res["detalles"] = enrich_computrabajo(portales.get("computrabajo", {}))
        res.update({"errores": errors, "empresas": report, "portales": preport, "gmail": greport})
        _save_state(last_search=time.time(), last_added=res["agregadas"])
        return res
    finally:
        _lock.release()


def scheduler_loop(stop):
    """Cada minuto mira si toca buscar según Configuración → Búsqueda automática."""
    while not stop.wait(60):
        try:
            auto = config.load().get("auto", {})
            if not auto.get("enabled"):
                continue
            every = max(1, float(auto.get("every_hours", 6))) * 3600
            if time.time() - load_state().get("last_search", 0) >= every:
                run_search()
        except Exception as e:  # el planificador nunca debe caerse
            print("Búsqueda automática falló:", e)
