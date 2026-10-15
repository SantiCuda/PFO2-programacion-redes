"""
PFO 2 - Sistema de Gestión de Tareas con API y Base de Datos
Servidor: API REST con Flask + SQLite

Endpoints:
  POST /registro  -> registra un usuario (contraseña hasheada)
  POST /login     -> verifica credenciales y abre una sesión
  POST /logout    -> cierra la sesión
  GET  /tareas    -> HTML de bienvenida (requiere sesión o HTTP Basic Auth)
"""
import os
import sqlite3
from functools import wraps

from flask import Flask, request, jsonify, g, Response, session
from markupsafe import escape
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = "tareas.db"

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))  # firma la cookie de sesión
app.json.ensure_ascii = False  # muestra "contraseña" con ñ en las respuestas JSON


# ---------------------------------------------------------------- Base de datos
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario       TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
            """
        )


def verificar_credenciales(usuario, contrasena):
    fila = get_db().execute(
        "SELECT password_hash FROM usuarios WHERE usuario = ?", (usuario,)
    ).fetchone()
    return fila is not None and check_password_hash(fila["password_hash"], contrasena)


def leer_credenciales_json():
    datos = request.get_json(silent=True) or {}
    usuario = (datos.get("usuario") or "").strip()
    contrasena = datos.get("contraseña") or datos.get("contrasena") or ""
    return usuario, contrasena


# --------------------------------------------------------------- Autenticación
def requiere_auth(f):
    """Permite el acceso si hay sesión iniciada (POST /login)
    o si el pedido trae credenciales válidas por HTTP Basic Auth."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        usuario = session.get("usuario")
        if not usuario:
            auth = request.authorization
            if auth and verificar_credenciales(auth.username, auth.password):
                usuario = auth.username
        if not usuario:
            return Response(
                "Acceso denegado: iniciá sesión o enviá credenciales válidas.\n",
                401,
                {"WWW-Authenticate": 'Basic realm="Tareas"'},
            )
        return f(usuario, *args, **kwargs)

    return wrapper


# -------------------------------------------------------------------- Endpoints
@app.post("/registro")
def registro():
    usuario, contrasena = leer_credenciales_json()
    if not usuario or not contrasena:
        return jsonify(error="Se requieren 'usuario' y 'contraseña'."), 400

    try:
        get_db().execute(
            "INSERT INTO usuarios (usuario, password_hash) VALUES (?, ?)",
            (usuario, generate_password_hash(contrasena)),
        )
        get_db().commit()
    except sqlite3.IntegrityError:
        return jsonify(error=f"El usuario '{usuario}' ya existe."), 409

    return jsonify(mensaje=f"Usuario '{usuario}' registrado correctamente."), 201


@app.post("/login")
def login():
    usuario, contrasena = leer_credenciales_json()
    if not usuario or not contrasena:
        return jsonify(error="Se requieren 'usuario' y 'contraseña'."), 400

    if not verificar_credenciales(usuario, contrasena):
        return jsonify(error="Usuario o contraseña incorrectos."), 401

    session["usuario"] = usuario
    return jsonify(mensaje=f"Login exitoso. Bienvenido/a, {usuario}."), 200


@app.post("/logout")
def logout():
    session.clear()
    return jsonify(mensaje="Sesión cerrada."), 200


@app.get("/tareas")
@requiere_auth
def tareas(usuario):
    html = f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Gestor de Tareas</title>
  <style>
    body {{ font-family: system-ui, sans-serif; background:#f4f6f8; display:flex;
           justify-content:center; align-items:center; height:100vh; margin:0; }}
    .card {{ background:#fff; padding:2rem 3rem; border-radius:12px;
            box-shadow:0 4px 16px rgba(0,0,0,.1); text-align:center; }}
    h1 {{ color:#2b4c7e; margin-top:0; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>¡Bienvenido/a, {escape(usuario)}!</h1>
    <p>Accediste correctamente al Sistema de Gestión de Tareas.</p>
  </div>
</body>
</html>"""
    return Response(html, mimetype="text/html")


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
