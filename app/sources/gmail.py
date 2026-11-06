"""Alertas de empleo por Gmail (IMAP, solo lectura).

Los portales mandan mails con las ofertas nuevas de tus alertas. Acá se leen los mails
recientes de esos portales y se sacan los links que parecen puestos de trabajo.
No modifica la casilla: abre la carpeta en modo solo lectura y no marca nada como leído.

Requiere una "contraseña de aplicación" de Google (la contraseña normal no sirve).
"""
import email
import imaplib
import re
from datetime import datetime, timedelta, timezone
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

from ..scoring import norm
from .companies import _Links

DEFAULT_SENDERS = ["computrabajo", "bumeran", "linkedin", "indeed", "zonajobs", "jooble", "workana", "glassdoor"]
PORTAL_NAMES = {"computrabajo": "Computrabajo", "bumeran": "Bumeran", "linkedin": "LinkedIn", "indeed": "Indeed",
                "zonajobs": "ZonaJobs", "jooble": "Jooble", "workana": "Workana", "glassdoor": "Glassdoor"}

# Textos de botones y pie de mail que no son puestos de trabajo.
NOT_JOBS = ("darse de baja", "desuscrib", "cancelar suscripcion", "ver mas", "ver todas", "ver todos", "ver oferta",
            "ver empleo", "ver trabajo", "ver ofertas", "configur", "politica", "privacidad", "terminos", "ayuda",
            "descarg", "postular", "aplicar", "iniciar sesion", "ingresar", "crear alerta", "editar alerta",
            "administrar", "preferencias", "unsubscribe", "ver en el navegador", "mi cuenta", "ver el correo",
            "mas empleos", "buscar empleo", "contacto", "app store", "google play", "facebook", "instagram", "twitter")


def _header(msg, name):
    try:
        return str(make_header(decode_header(msg.get(name, ""))))
    except Exception:
        return msg.get(name, "") or ""


def _html_body(msg):
    parts = msg.walk() if msg.is_multipart() else [msg]
    for part in parts:
        if part.get_content_type() == "text/html":
            payload = part.get_payload(decode=True) or b""
            return payload.decode(part.get_content_charset() or "utf-8", "replace")
    return ""


def parse_message(msg, senders):
    """Devuelve las ofertas que se pueden leer en un mail, o [] si no es de un portal conocido."""
    sender = norm(_header(msg, "From"))
    portal = next((s for s in senders if norm(s) in sender), None)
    if not portal:
        return []
    posted = None
    try:
        posted = parsedate_to_datetime(msg["Date"]).astimezone(timezone.utc).isoformat()
    except Exception:
        pass
    parser = _Links()
    parser.feed(_html_body(msg))
    jobs, seen = [], set()
    for text, href in parser.links:
        n = norm(text)
        if not 8 <= len(text) <= 120 or not href.startswith("http") or any(b in n for b in NOT_JOBS):
            continue
        if re.fullmatch(r"[\W\d_]+", text) or text.lower().startswith("http"):
            continue
        key = (n, urlparse(href).path)
        if key in seen:
            continue
        seen.add(key)
        jobs.append({"title": text, "company": "", "location": "", "description": f"Llegó por alerta de {PORTAL_NAMES.get(portal, portal)}.",
                     "posted": posted, "source": f"Alerta {PORTAL_NAMES.get(portal, portal)}", "url": href})
    return jobs


def fetch(conf, password, timeout=30):
    """Devuelve (ofertas, informe). Lanza una excepción si no puede iniciar sesión."""
    senders = conf.get("senders") or DEFAULT_SENDERS
    since = (datetime.now() - timedelta(days=int(conf.get("days", 7)))).strftime("%d-%b-%Y")
    jobs, report = [], []
    box = imaplib.IMAP4_SSL("imap.gmail.com", timeout=timeout)
    try:
        box.login(conf["email"], password)
        box.select("INBOX", readonly=True)
        status, data = box.search(None, "SINCE", since)
        ids = data[0].split() if status == "OK" and data and data[0] else []
        for num in ids[-200:]:
            status, parts = box.fetch(num, "(BODY.PEEK[])")
            if status != "OK" or not parts or not isinstance(parts[0], tuple):
                continue
            msg = email.message_from_bytes(parts[0][1])
            found = parse_message(msg, senders)
            if found:
                jobs += found
                report.append({"correo": _header(msg, "Subject")[:80], "encontradas": len(found)})
    finally:
        try:
            box.logout()
        except Exception:
            pass
    return jobs, report
