"""
PFO 2 - Pruebas automáticas de la API.
Uso: con servidor.py corriendo, ejecutar  python pruebas.py
(desde la misma carpeta, para poder revisar tareas.db)
"""
import sqlite3
import time

import requests

BASE_URL = "http://127.0.0.1:5000"
USUARIO = f"prueba_{int(time.time())}"
CLAVE = "1234"
ok_total = 0
fallas = 0


def check(descripcion, condicion, detalle=""):
    global ok_total, fallas
    if condicion:
        ok_total += 1
        print(f"  [OK]    {descripcion}")
    else:
        fallas += 1
        print(f"  [FALLA] {descripcion}  -> {detalle}")


def cuerpo(r):
    try:
        return r.json()
    except ValueError:
        return r.text.strip()


print(f"Usuario de prueba: {USUARIO}\n")

print("1) Registro de usuarios - POST /registro")
r = requests.post(f"{BASE_URL}/registro", json={"usuario": USUARIO, "contraseña": CLAVE})
check("Registro de usuario nuevo -> 201", r.status_code == 201, cuerpo(r))
r = requests.post(f"{BASE_URL}/registro", json={"usuario": USUARIO, "contraseña": CLAVE})
check("Usuario duplicado -> 409", r.status_code == 409, cuerpo(r))
r = requests.post(f"{BASE_URL}/registro", json={"usuario": USUARIO})
check("Datos incompletos -> 400", r.status_code == 400, cuerpo(r))

print("\n2) Contraseña hasheada en SQLite")
try:
    con = sqlite3.connect("tareas.db")
    guardado = con.execute(
        "SELECT password_hash FROM usuarios WHERE usuario = ?", (USUARIO,)
    ).fetchone()[0]
    con.close()
    check("La contraseña NO está en texto plano", guardado != CLAVE, guardado)
    print(f"          valor guardado: {guardado[:60]}...")
except Exception as e:
    check("Leer tareas.db (correr desde la carpeta del servidor)", False, e)

print("\n3) Inicio de sesión - POST /login")
r = requests.post(f"{BASE_URL}/login", json={"usuario": USUARIO, "contraseña": "incorrecta"})
check("Contraseña incorrecta -> 401", r.status_code == 401, cuerpo(r))
r = requests.post(f"{BASE_URL}/login", json={"usuario": "no_existe_xyz", "contraseña": CLAVE})
check("Usuario inexistente -> 401", r.status_code == 401, cuerpo(r))

print("\n4) Acceso a tareas - GET /tareas")
r = requests.get(f"{BASE_URL}/tareas")
check("Sin login -> 401", r.status_code == 401, r.status_code)

sesion = requests.Session()
r = sesion.post(f"{BASE_URL}/login", json={"usuario": USUARIO, "contraseña": CLAVE})
check("Login correcto -> 200", r.status_code == 200, cuerpo(r))
r = sesion.get(f"{BASE_URL}/tareas")
check("Con sesión iniciada -> 200 + HTML de bienvenida",
      r.status_code == 200 and "text/html" in r.headers.get("Content-Type", "")
      and "Bienvenido" in r.text, r.status_code)

r = requests.get(f"{BASE_URL}/tareas", auth=(USUARIO, CLAVE))
check("Con HTTP Basic Auth -> 200", r.status_code == 200, r.status_code)

sesion.post(f"{BASE_URL}/logout")
r = sesion.get(f"{BASE_URL}/tareas")
check("Después de logout -> 401", r.status_code == 401, r.status_code)

print(f"\nResultado: {ok_total} OK, {fallas} fallas")
