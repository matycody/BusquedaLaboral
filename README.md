# Buscador de empleo

Buscador de empleo local: junta ofertas de varias fuentes, agrupa duplicados, les pone un puntaje de 0 a 100 y recomienda cuál de tus dos CV usar (electricidad o programación). Todo se maneja desde la página web.

No necesita instalar nada extra: solo **Python 3.9 o superior** (usa solo la librería estándar).

## Cómo levantarlo

```bash
python run.py          # Windows: py run.py
```

Después abrí http://127.0.0.1:8000 (o `python run.py 9000` para otro puerto).

## Qué hace hoy

- **Ofertas de ejemplo**: en Configuración → Datos (o desde la pantalla vacía) cargás ofertas de prueba, con duplicados entre portales para ver el agrupado.
- **Buscar ofertas**: lee las fuentes RSS cargadas en ⚙ Configuración.
- **+ Agregar oferta**: pegás un aviso a mano (sirve para cualquier portal).
- **Mis empresas** (Genrod, Edesur, Coto, Mercado Libre, Ualá): panel con link a su página de empleos o búsqueda en LinkedIn; sus ofertas suman +10 puntos, llevan la etiqueta "Mi empresa" y se pueden filtrar. Si cargás el link de empleos, **Buscar ofertas** lo revisa y trae los puestos que se leen en el HTML (las páginas que cargan con JavaScript pueden salir vacías; en ese caso se avisa).
- **Filtros**: texto, lugar, CV recomendado, estado, puntaje mínimo.
- **Estados**: me interesa / apliqué / descartada.
- **Configuración**: lugares que te sirven, palabras clave y pesos por CV, penalizaciones (senior, gerente, "5 años"…). Al guardar se recalculan todos los puntajes.

## Cómo se calcula el puntaje

1. Se compara cada oferta con las palabras clave de cada CV (en el título pesa el doble que en la descripción).
2. Gana el CV con más coincidencia: ese es el recomendado.
3. Se suman bonos por lugar (te sirve / remoto) y por ser reciente, y se restan penalizaciones.

## Estructura

```
run.py                  arranca el servidor
app/server.py           servidor y API (sin dependencias)
app/scoring.py          puntaje y recomendación de CV
app/db.py               base SQLite + agrupado de duplicados
app/config.py           configuración (data/config.json)
app/sources/demo.py     ofertas de ejemplo
app/sources/companies.py  revisa las páginas de empleo de tus empresas
app/sources/rss.py      lector genérico de feeds RSS/Atom
app/static/index.html   estructura de la página
app/static/styles.css   estilos
app/static/app.js       lógica de la página
data/                   tu base y configuración (NO se sube a GitHub)
```

## Pendiente / próximos pasos

- Fuentes por portal (Computrabajo, Bumeran, Indeed, LinkedIn, etc.): cada portal tiene sus reglas y bloquea scrapers, así que se agregan de a una en `app/sources/`.
- Alertas por Gmail.
