"""Configuración persistente (data/config.json). Todo se edita desde la web."""
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE, "data")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")

DEFAULT = {
    "location": "",
    "busquedas": [],
    "locations_ok": ["capital federal", "caba", "buenos aires", "remoto"],
    "min_score": 0,
    "profiles": {
        "electricidad": {
            "label": "CV Electricidad",
            "keywords": {
                "electricista": 10, "tablerista": 10, "montador": 8, "plc": 8, "logo": 6,
                "automatismos": 8, "siemens": 6, "mantenimiento": 5, "instalaciones": 5,
                "industrial": 4, "baja tension": 6, "media tension": 4, "tableros": 8,
                "ayudante": 3, "operario": 2, "pasante": 3,
            },
        },
        "programacion": {
            "label": "CV Programación",
            "keywords": {
                "programador": 10, "desarrollador": 10, "developer": 10, "python": 8,
                "javascript": 7, "sql": 6, "datos": 5, "data": 5, "analista": 5,
                "junior": 8, "trainee": 8, "pasante": 4, "backend": 6, "frontend": 6,
                "web": 4, "soporte": 3, "qa": 4, "ciencia de datos": 6,
            },
        },
    },
    "penalize": {"senior": -15, "semi senior": -8, "ssr": -8, "lider": -10, "gerente": -20, "5 años": -12, "3 años": -6},
    "empresas": [
        {"name": "Genrod", "url": ""},
        {"name": "Edesur", "url": ""},
        {"name": "Coto", "url": "https://www.coto.com.ar/empleos/"},
        {"name": "Mercado Libre", "url": "https://careers-meli.mercadolibre.com/"},
        {"name": "Ualá", "url": "https://www.ua.la/sumate"},
    ],
    "company_bonus": 10,
    "auto": {"enabled": False, "every_hours": 6},
    "avisos": {"puntaje": 80, "seguimiento_dias": 7},
    "postulacion": {
        "nombre": "",
        "telefono": "",
        "plantillas": {
            "electricidad": (
                "Hola, buenos días.\n\nMe postulo para el puesto de {puesto} en {empresa}. "
                "Busco mi primera experiencia laboral en el rubro eléctrico y tengo muchas ganas de aprender y sumarme al equipo.\n\n"
                "Adjunto mi CV ({cv}). Quedo a disposición para una entrevista.\n\nSaludos,\n{nombre}\n{telefono}"
            ),
            "programacion": (
                "Hola, buenos días.\n\nMe postulo para el puesto de {puesto} en {empresa}. "
                "Estoy estudiando programación y busco mi primera experiencia laboral para seguir creciendo.\n\n"
                "Adjunto mi CV ({cv}) con mis proyectos. Quedo a disposición para una entrevista.\n\nSaludos,\n{nombre}\n{telefono}"
            ),
        },
    },
    "gmail": {"enabled": False, "email": "", "days": 7,
              "senders": ["computrabajo", "bumeran", "linkedin", "indeed", "zonajobs", "jooble", "workana", "glassdoor"]},
    "portales": {
        "computrabajo": {
            "enabled": True,
            "region": "buenos-aires-gba",
            "max_pages": 2,
            "queries": ["electricista", "ayudante electricista", "tablerista", "mantenimiento electrico",
                        "programador", "desarrollador web", "desarrollador python", "analista de datos", "soporte tecnico"],
        },
        "talent": {
            "enabled": True,
            "location": "Buenos Aires",
            "queries": ["electricista", "tablerista", "mantenimiento electrico",
                        "programador junior", "desarrollador web", "analista de datos"],
        },
        "linkedin": {
            "enabled": False,
            "max_pages": 1,
            "location": "Buenos Aires, Argentina",
            "queries": ["electricista", "programador junior", "analista de datos"],
        },
        "jooble": {
            "enabled": False,
            "max_pages": 2,
            "location": "Buenos Aires",
            "queries": ["electricista", "tablerista", "mantenimiento electrico",
                        "programador junior", "desarrollador web", "analista de datos"],
        },
        "buscojobs": {
            "enabled": True,
            "max_pages": 2,
            "zonas": ["buenos aires", "capital federal", "caba", "remoto"],
            "queries": ["electricista", "ayudante electricista", "tablerista", "mantenimiento electrico",
                        "programador", "desarrollador web", "analista de datos", "soporte tecnico"],
        },
        "zonajobs": {
            "enabled": True,
            "max_pages": 2,
            "zonas": ["buenos aires", "capital federal", "caba", "remoto"],
            "queries": ["electricista", "ayudante electricista", "tablerista", "mantenimiento electrico",
                        "programador", "desarrollador web", "analista de datos", "soporte tecnico"],
        },
        "bumeran": {
            "enabled": True,
            "max_pages": 2,
            "zonas": ["buenos aires", "capital federal", "caba", "remoto"],
            "queries": ["electricista", "ayudante electricista", "tablerista", "mantenimiento electrico",
                        "programador", "desarrollador web", "desarrollador python", "analista de datos", "soporte tecnico"],
        },
    },
    "rss_feeds": [],
}


def load():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(CONFIG_PATH):
        save(DEFAULT)
        return json.loads(json.dumps(DEFAULT))
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = json.load(f)
    for k, v in DEFAULT.items():
        cfg.setdefault(k, v)
    if "busquedas" not in cfg:  # configuraciones viejas: unir los puestos que tenía cada portal
        union = []
        for p in (cfg.get("portales") or {}).values():
            for q in p.get("queries", []):
                if q not in union:
                    union.append(q)
        cfg["busquedas"] = union
        cfg["setup_done"] = True  # quien ya venía usando la app no necesita el asistente
    return cfg


def save(cfg):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


SECRETS_PATH = os.path.join(DATA_DIR, "secrets.json")


def get_secret(name, env=None):
    """Primero la variable de entorno (si se indica), después data/secrets.json."""
    if env and os.environ.get(env):
        return os.environ[env]
    try:
        with open(SECRETS_PATH, encoding="utf-8") as f:
            return json.load(f).get(name, "")
    except (OSError, ValueError):
        return ""


def set_secret(name, value):
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        with open(SECRETS_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {}
    if value:
        data[name] = value
    else:
        data.pop(name, None)
    with open(SECRETS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f)
    try:
        os.chmod(SECRETS_PATH, 0o600)
    except OSError:
        pass
