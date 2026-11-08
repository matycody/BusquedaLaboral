"""Arranca el servidor:  python run.py   (luego abrir http://127.0.0.1:8000)

Olvidaste tu contraseña:  python run.py --reset-password tu@correo.com NuevaClave123
"""
import sys

from app import users
from app.server import run

if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--reset-password":
        try:
            users.reset_password(sys.argv[2], sys.argv[3])
            print("Listo: contraseña cambiada. Ya podés ingresar.")
        except users.AuthError as e:
            print("No se pudo:", e)
        sys.exit(0)
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    run(port=port)
