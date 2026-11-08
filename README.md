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
- **Talent.com** (primera página de cada búsqueda) y **LinkedIn** (lista pública, apagado por defecto: sus términos no permiten la lectura automática; usalo con moderación o preferí las alertas por Gmail).
- **Jooble** (opcional): agregador de muchos sitios, por su API oficial. Pedí una clave gratuita en jooble.org/api/about, pegala en ⚙ Configuración → Jooble y activalo.
- **Pantalla**: lista de ofertas a la izquierda y detalle a la derecha (en el celular, el detalle ocupa toda la pantalla). Cada oferta muestra una etiqueta de calidad, el desglose "por qué este puntaje" y qué CV conviene. Atajos: ↑ ↓ para moverte, S guardar, D descartar, A aplicada.
- **Avisos**: cuando aparece una oferta nueva con puntaje alto (80 por defecto) te avisa en pantalla y, si lo permitís, con una notificación del navegador. Las postulaciones sin novedades después de unos días (7 por defecto) se marcan con "Hacer seguimiento". Ambos valores se cambian en ⚙ Configuración → Avisos.
- **Exportar**: en las pestañas Aplicadas y Me interesa, el botón "Exportar a planilla" baja un archivo que abre Excel o Google Sheets, con puesto, empresa, puntaje, CV usado, fecha de postulación, link y notas.
- **Buscar ofertas**: lee Computrabajo, Bumeran, ZonaJobs y BuscoJobs (puestos y zona configurables), las páginas de tus empresas, tus alertas de Gmail y los feeds RSS cargados en ⚙ Configuración.
- **+ Agregar oferta**: pegás un aviso a mano (sirve para cualquier portal).
- **Alertas por Gmail**: lee (solo lectura) los mails de alertas de los portales y los suma a la lista. Hace falta una contraseña de aplicación de Google (verificación en 2 pasos + myaccount.google.com/apppasswords). Se guarda en `data/secrets.json`, que no se sube a GitHub; también podés usar la variable de entorno `GMAIL_APP_PASSWORD`. Después creá alertas de empleo en cada portal con ese mismo mail.
- **Búsqueda automática**: en Configuración elegís cada cuántas horas busca sola (mientras el programa esté abierto). Las ofertas de las últimas 24 h llevan la etiqueta "Nueva" y la lista se actualiza sola.
- **Preparar postulación**: en el detalle de cada oferta arma el asunto y el mensaje con el CV recomendado. Podés copiarlo, abrirlo en Gmail, abrir la oferta y marcarla como aplicada. No envía nada por vos. Tu nombre, teléfono y las plantillas se editan en Configuración → Postulación y quedan en `data/`, que no se sube a GitHub.
- **Mis empresas** (Genrod, Edesur, Coto, Mercado Libre, Ualá): panel con link a su página de empleos o búsqueda en LinkedIn; sus ofertas suman +10 puntos, llevan la etiqueta "Mi empresa" y se pueden filtrar. Si cargás el link de empleos, **Buscar ofertas** lo revisa. Mercado Libre (puestos de Argentina) y Ualá tienen lector propio; las demás usan un lector genérico que solo ve lo que está en el HTML, y si una página sale vacía se avisa.
- **Filtros**: texto, lugar, CV recomendado, estado, puntaje mínimo.
- **Estados**: me interesa / apliqué / descartada.
- **Configuración**: lugares que te sirven, palabras clave y pesos por CV, penalizaciones (senior, gerente, "5 años"…). Al guardar se recalculan todos los puntajes.

## Cómo se calcula el puntaje

1. Se compara cada oferta con las palabras clave de cada CV (en el título pesa el doble que en la descripción).
2. Gana el CV con más coincidencia: ese es el recomendado.
3. Se suman bonos por lugar (te sirve / remoto), por ser reciente y por ser abierta a primer empleo (junior, pasante, "sin experiencia"). Se restan penalizaciones por puestos senior o "SR/SSR", por pedir años de experiencia (más años, más resta) y por llevar mucho tiempo publicada.

## Estructura

```
run.py                  arranca el servidor
app/server.py           servidor y API (sin dependencias)
app/scoring.py          puntaje y recomendación de CV
app/search.py           búsqueda completa y planificador automático
app/db.py               base SQLite + agrupado de duplicados
app/config.py           configuración (data/config.json)
app/sources/demo.py     ofertas de ejemplo
app/sources/companies.py  lectores de las páginas de empleo (Mercado Libre, Ualá y genérico)
app/sources/computrabajo.py  lector de Computrabajo Argentina
app/sources/gmail.py         alertas de empleo desde Gmail (IMAP, solo lectura)
app/sources/bumeran.py       lector de Bumeran Argentina (API interna de su sitio)
app/sources/zonajobs.py      lector de ZonaJobs (misma API que Bumeran)
app/sources/buscojobs.py     lector de BuscoJobs (JSON embebido en la página de resultados)
app/sources/rss.py      lector genérico de feeds RSS/Atom
app/static/index.html   estructura de la página
app/static/styles.css   estilos
app/static/app.js       lógica de la página
data/                   tu base y configuración (NO se sube a GitHub)
```

## Pendiente / próximos pasos

- Más portales (Indeed, LinkedIn, etc.): cada portal tiene sus reglas y bloquea scrapers, así que se agregan de a una en `app/sources/`.


## Rubro y puestos a buscar

La primera vez que se abre la app pregunta qué trabajo buscás (salud, construcción, ventas, administración, logística, gastronomía, educación, electricidad, programación, limpieza/seguridad, o puestos propios). Con eso se arman los **puestos que se buscan en todos los portales** y el puntaje de cada oferta. Se puede cambiar en Configuración → Portales → "Cambiar de rubro". Las configuraciones anteriores se migran solas.

## Mientras busca

Aparece un cartel con el avance por fuente (portales, empresas, Gmail, guardado). Las alertas de Computrabajo que llegan por Gmail ahora separan puesto, empresa, lugar y antigüedad.

## Registro inicial (perfil)

La primera vez se abre un asistente de 4 pasos: datos personales (nombre, correo, teléfono), rubro y puestos, zona/modalidad/nivel de experiencia y CV (opcional, se guarda en `data/cvs`). De ahí salen los puestos buscados, las zonas que sirven, las penalizaciones por nivel y los datos de las postulaciones. Se puede repetir desde Configuración → "Editar mi perfil y rubro".

Las ofertas que no nombran nada de lo que buscás se limitan a 10 puntos y quedan ocultas con el filtro "Relevantes" (el de por defecto); "Todas" las muestra.

## Postularse en ventana lateral

"Abrir oferta" abre el aviso en una ventana al costado (55% del ancho, a la derecha). Al volver a la app o cerrar esa ventana, pregunta "¿Te postulaste a…?": **Sí, apliqué** la marca como aplicada y pasa a la siguiente oferta; **Todavía no** la deja como está; **No me sirve** la descarta. Los portales no permiten mostrarse dentro de la propia app (bloquean los marcos), por eso es una ventana aparte. Si el navegador bloquea ventanas emergentes, se abre como pestaña común.

## Cuentas

Al abrir la app hay que **crear una cuenta** (nombre, correo y contraseña de 8+ caracteres) o ingresar. Cada cuenta tiene su propia carpeta en `data/users/<id>/` con su perfil, ofertas, CV, claves (Gmail, Jooble) y búsqueda automática; una cuenta no ve los datos de otra. La primera cuenta que se crea se queda con los datos que ya hubiera de la versión sin cuentas.

- Las contraseñas se guardan con PBKDF2-SHA256 (200 mil vueltas y sal propia), nunca en texto. La sesión dura 30 días y se cierra desde **Mi cuenta → Cerrar sesión**.
- Tras 5 intentos fallidos se bloquea el ingreso de ese correo por 10 minutos.
- **Mi cuenta** permite cambiar la contraseña (cierra las demás sesiones), editar el perfil y eliminar la cuenta con todos sus datos.
- Si olvidaste la contraseña: `python run.py --reset-password tu@correo.com NuevaClave123` (hace falta acceso a la carpeta del programa).
- El servidor escucha solo en `127.0.0.1`. Para abrirlo a otras personas habría que ponerlo detrás de HTTPS y de un dominio; no está hecho.
