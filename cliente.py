"""
PFO 2 - Cliente de consola para la API de Tareas
Requiere que servidor.py esté corriendo en http://127.0.0.1:5000
"""
import getpass
import os
import re
import tempfile
import webbrowser
from html import unescape

import requests

BASE_URL = "http://127.0.0.1:5000"

# requests.Session guarda la cookie que devuelve /login,
# así los pedidos siguientes a /tareas quedan autenticados.
http = requests.Session()
usuario_actual = None


def pedir_credenciales():
    usuario = input("Usuario: ").strip()
    contrasena = getpass.getpass("Contraseña (no se muestra): ").strip()
    return usuario, contrasena


def mostrar(resp):
    try:
        datos = resp.json()
        print(f"[{resp.status_code}] {datos.get('mensaje') or datos.get('error')}")
    except ValueError:
        print(f"[{resp.status_code}] {resp.text.strip()}")


def html_a_texto(html):
    cuerpo = re.search(r"<body.*?>(.*)</body>", html, re.S)
    texto = re.sub(r"<[^>]+>", "\n", cuerpo.group(1) if cuerpo else html)
    lineas = [unescape(l.strip()) for l in texto.splitlines() if l.strip()]
    return "\n".join(lineas)


def registrar():
    usuario, contrasena = pedir_credenciales()
    resp = http.post(f"{BASE_URL}/registro",
                     json={"usuario": usuario, "contraseña": contrasena})
    mostrar(resp)


def login():
    global usuario_actual
    usuario, contrasena = pedir_credenciales()
    resp = http.post(f"{BASE_URL}/login",
                     json={"usuario": usuario, "contraseña": contrasena})
    mostrar(resp)
    if resp.ok:
        usuario_actual = usuario


def ver_tareas(abrir_navegador=False):
    resp = http.get(f"{BASE_URL}/tareas")
    if resp.status_code != 200:
        mostrar(resp)
        return
    print(f"[200]\n{html_a_texto(resp.text)}")
    if abrir_navegador:
        ruta = os.path.join(tempfile.gettempdir(), "tareas_bienvenida.html")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(resp.text)
        webbrowser.open(f"file://{ruta}")


def logout():
    global usuario_actual
    mostrar(http.post(f"{BASE_URL}/logout"))
    usuario_actual = None


OPCIONES = {
    "1": ("Registrarse", registrar),
    "2": ("Iniciar sesión", login),
    "3": ("Ver tareas", ver_tareas),
    "4": ("Ver tareas en el navegador", lambda: ver_tareas(abrir_navegador=True)),
    "5": ("Cerrar sesión", logout),
}


def main():
    while True:
        estado = f"sesión: {usuario_actual}" if usuario_actual else "sin sesión"
        print(f"\n=== Gestor de Tareas ({estado}) ===")
        for k, (texto, _) in OPCIONES.items():
            print(f"{k}. {texto}")
        print("0. Salir")
        op = input("Opción: ").strip()
        if op == "0":
            print("Chau.")
            break
        if op not in OPCIONES:
            print("Opción inválida.")
            continue
        try:
            OPCIONES[op][1]()
        except requests.ConnectionError:
            print("No se pudo conectar con el servidor. ¿Está corriendo servidor.py?")


if __name__ == "__main__":
    main()
