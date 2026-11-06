"""Configuración persistente (data/config.json). Todo se edita desde la web."""
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE, "data")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")

DEFAULT = {
    "location": "Claypole, Buenos Aires",
    "locations_ok": ["claypole", "almirante brown", "lomas de zamora", "quilmes", "caba", "capital federal", "remoto"],
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
    "companies": [],
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
    return cfg


def save(cfg):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
