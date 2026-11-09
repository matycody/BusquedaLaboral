# Publicarlo en internet para que lo usen otras personas

Hoy el programa corre en tu computadora. Estos pasos lo dejan en un servidor con HTTPS. **No lo abras al público sin HTTPS**: las contraseñas viajarían sin cifrar.

## Qué hace el modo público (`BL_PUBLIC=1`)
- Permite crear cuentas desde internet (máximo 5 por hora por conexión).
- Marca la cookie de sesión como `Secure` y envía `Strict-Transport-Security`.
- Lee la IP real desde `X-Forwarded-For` (la pone el proxy HTTPS).
- Limita los pedidos de mails (10 por hora por conexión y 3 por correo).
- Cabeceras `X-Frame-Options`, `nosniff` y `Referrer-Policy` (están siempre activas).

## ¿Vercel o Render?
**Render.** Vercel ejecuta funciones que se apagan después de cada pedido y no tienen disco: esta app necesita un proceso que quede encendido (busca ofertas sola cada tanto) y guarda cuentas, CVs y una base SQLite en disco. En Vercel se perderían los datos y la búsqueda automática. Render (o Railway, Fly.io o un VPS) sí corre un servidor permanente con disco.

## Publicarlo en Render
1. Subí el repositorio (el limpio, ver abajo) a GitHub.
2. En Render: **New → Blueprint** y elegí el repositorio. Lee `render.yaml` y crea el servicio con un disco de 1 GB. Necesita un plan pago (el gratuito no tiene disco persistente y se duerme).
3. Cuando Render te dé la URL, cargala en la variable `BL_BASE_URL` (los links de los mails se arman con ella). Si usás dominio propio, agregalo en Render y usá ese.
4. Cargá `BL_OPERADOR` (tu nombre o razón social) y `BL_CONTACTO` (correo de contacto): aparecen en los términos y en la política de privacidad.
5. Cargá `BREVO_API_KEY` y `BREVO_SENDER_EMAIL` (ver más abajo) y esperá el deploy. Render pone el HTTPS solo.

## Correos con Brevo (confirmación y recuperación de contraseña)
1. Creá una cuenta en brevo.com (plan gratis: 300 mails por día).
2. **Remitentes y dominios → Agregar un remitente** y confirmá el correo que te llega. Idealmente verificá tu dominio (DKIM) para que no caiga en spam.
3. **SMTP y API → Claves de API → Generar una clave**.
4. Cargá la clave en `BREVO_API_KEY` y el remitente en `BREVO_SENDER_EMAIL`.

Con esas dos variables, las cuentas nuevas deben confirmar el correo para ingresar y aparece «¿Olvidaste tu contraseña?». Sin ellas, el programa funciona igual (modo local). Las cuentas creadas antes de activar los mails cuentan como confirmadas.

## Otra opción: un servidor propio con Docker
Un VPS chico con Docker y un dominio apuntando a su IP. En `docker-compose.yml` cambiá `empleo.tudominio.com` por tu dominio y ejecutá `docker compose up -d`; Caddy consigue el HTTPS solo. Los datos quedan en `./data`: copialos seguido.

## Antes de abrirlo a desconocidos (pendiente)
- [ ] **Revisar con un abogado los términos y la privacidad** (`app/static/terminos.html` y `privacidad.html`): son un modelo general. Se piden al registrarse y queda guardada la versión aceptada. Si cambiás el texto, subí `LEGAL_VERSION` en `app/server.py`.
- [ ] **Inscribir la base de datos ante la AAIP** (Registro Nacional de Bases de Datos Personales), obligación de la Ley 25.326 para quien administra datos de terceros.
- [ ] **Contraseña de Gmail**: la contraseña de aplicación queda en un archivo del servidor sin cifrar (la política lo avisa). Para un servicio con muchos usuarios conviene cifrarla o quitar esa función del modo público.
- [ ] **Búsquedas desde un solo servidor**: todas las cuentas buscarían desde la misma IP y los portales pueden bloquearla. Conviene cachear búsquedas comunes entre usuarios.
- [ ] **Copias de seguridad automáticas** del disco; SQLite alcanza para decenas de usuarios, no para miles.
- [ ] **Condiciones de uso de cada portal**: revisá que permitan mostrar sus ofertas en un servicio con otros usuarios (Remotive, por ejemplo, prohíbe reenviarlas a terceros).
- [ ] **Repositorio limpio** (ver abajo): se hace una sola vez, justo antes de publicar.

## Limpiar el historial del repositorio
El historial viejo contiene datos personales. Lo más seguro es crear un repositorio nuevo con el código actual (sin `.git`) y dejar el viejo privado:
```
git clone https://github.com/matycody/BusquedaLaboral.git limpio && cd limpio
rm -rf .git && git init -b main && git add -A && git commit -m "Primera versión pública"
```
Antes, confirmá que no queden datos tuyos en los archivos (`grep -ri "tu-apellido" .`).
