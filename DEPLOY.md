# Publicarlo en internet para que lo usen otras personas

Hoy el programa corre en tu computadora. Estos pasos lo dejan en un servidor con HTTPS. **No lo abras al público sin HTTPS**: las contraseñas viajarían sin cifrar.

## Qué hace el modo público (`BL_PUBLIC=1`)
- Permite crear cuentas desde internet (máximo 5 por hora por conexión).
- Marca la cookie de sesión como `Secure` y envía `Strict-Transport-Security`.
- Lee la IP real desde `X-Forwarded-For` (la pone el proxy HTTPS).
- Cabeceras `X-Frame-Options`, `nosniff` y `Referrer-Policy` (están siempre activas).

## Opción simple: un servidor con Docker
1. Un VPS chico (1 GB de RAM alcanza para empezar) con Docker instalado y un dominio apuntando a su IP.
2. Copiá el proyecto al servidor y en `docker-compose.yml` cambiá `empleo.tudominio.com` por tu dominio.
3. `docker compose up -d`. Caddy consigue el certificado HTTPS solo.
4. Los datos quedan en `./data`: hacé copia de esa carpeta.

## Antes de abrirlo a desconocidos (pendiente)
- [ ] **Verificación de correo y recuperación de contraseña**: hoy se recupera con `python run.py --reset-password` en el servidor. Hace falta un servicio de envío de mails (SMTP, Brevo, Resend…).
- [ ] **Términos y política de privacidad**: guardás CVs y datos personales; en Argentina aplica la Ley 25.326 de protección de datos personales.
- [ ] **Búsquedas desde un solo servidor**: todas las cuentas buscarían desde la misma IP y los portales pueden bloquearla. Conviene cachear búsquedas comunes entre usuarios.
- [ ] **Base de datos y copias de seguridad automáticas**; SQLite alcanza para decenas de usuarios, no para miles.
- [ ] **Condiciones de uso de cada portal**: revisá que permitan mostrar sus ofertas en un servicio con otros usuarios (Remotive, por ejemplo, prohíbe reenviarlas a terceros).
- [ ] **Limpiar el historial de git** de datos personales antes de hacer público el repositorio (ver abajo).

## Limpiar el historial del repositorio
El historial viejo contiene datos personales. Lo más seguro es crear un repositorio nuevo con el código actual (sin `.git`) y dejar el viejo privado:
```
git clone https://github.com/matycody/BusquedaLaboral.git limpio && cd limpio
rm -rf .git && git init -b main && git add -A && git commit -m "Primera versión pública"
```
Antes, confirmá que no queden datos tuyos en los archivos (`grep -ri "tu-apellido" .`).
