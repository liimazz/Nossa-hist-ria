"""
Nossa História — Guilherme & Julia
Flask + SQLite. Visitantes curtem e comentam sem login;
só quem tem conta (vocês dois) consegue postar e apagar.
"""
import os
import secrets
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

from flask import (Flask, abort, g, jsonify, redirect, render_template,
                   request, send_from_directory, session, url_for, flash)
from werkzeug.security import check_password_hash

try:
    from PIL import Image, ImageOps
except ImportError:  # Pillow é opcional; sem ele as fotos são salvas como vieram
    Image = None

# ----------------------------------------------------------------- CONFIG
NOME_1 = "Guilherme"
NOME_2 = "Julia"
INICIO_NAMORO = "2026-07-11T22:30:00-03:00"   # horário de Brasília/Natal
INICIO_TEXTO = "11 de julho de 2026 · 22:30"
FRASE_INICIAL = "Um cantinho só nosso, feito de momentos, carinho e muito amor."

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
UPLOADS = BASE / "uploads"
DATA.mkdir(exist_ok=True)
UPLOADS.mkdir(exist_ok=True)
DB_PATH = DATA / "nossa_historia.db"

EXT_FOTO = {"jpg", "jpeg", "png", "webp", "gif"}
EXT_VIDEO = {"mp4", "webm", "mov", "m4v"}
MAX_MB = 80

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]

# -------------------------------------------------------------------- APP
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = (MAX_MB + 5) * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 24 * 30


def _secret_key():
    f = DATA / "secret.key"
    if not f.exists():
        f.write_text(secrets.token_hex(32))
    return f.read_text().strip()


app.secret_key = os.environ.get("SECRET_KEY") or _secret_key()


# --------------------------------------------------------------- BANCO
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH, timeout=15)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    con = sqlite3.connect(DB_PATH)
    con.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        display_name TEXT NOT NULL,
        password_hash TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS posts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kind TEXT NOT NULL CHECK(kind IN ('photo','video','letter')),
        title TEXT NOT NULL DEFAULT '',
        body TEXT NOT NULL DEFAULT '',
        filename TEXT,
        event_date TEXT NOT NULL,
        author TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS likes(
        post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
        visitor TEXT NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY(post_id, visitor)
    );
    CREATE TABLE IF NOT EXISTS comments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
        visitor TEXT NOT NULL,
        name TEXT NOT NULL,
        text TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS login_fail(
        ip TEXT NOT NULL,
        at REAL NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_comments_post ON comments(post_id);
    """)
    con.commit()
    con.close()


init_db()


def agora():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


# --------------------------------------------------------------- HELPERS
@app.template_filter("datebr")
def datebr(s):
    try:
        y, m, d = str(s)[:10].split("-")
        return f"{int(d)} de {MESES[int(m) - 1]} de {y}"
    except Exception:
        return ""


@app.before_request
def identificar_visitante():
    g.vid = request.cookies.get("vid")
    g.novo_vid = False
    if not g.vid or len(g.vid) != 32:
        g.vid = uuid.uuid4().hex
        g.novo_vid = True


@app.after_request
def cookie_visitante(resp):
    if getattr(g, "novo_vid", False):
        resp.set_cookie("vid", g.vid, max_age=60 * 60 * 24 * 365 * 3,
                        httponly=True, samesite="Lax")
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    return resp


def usuario_atual():
    uid = session.get("uid")
    if not uid:
        return None
    return get_db().execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()


@app.context_processor
def contexto():
    return dict(user=usuario_atual(), NOME_1=NOME_1, NOME_2=NOME_2,
                INICIO_NAMORO=INICIO_NAMORO, INICIO_TEXTO=INICIO_TEXTO,
                FRASE_INICIAL=FRASE_INICIAL, csrf=csrf_token())


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]


def exige_login(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if not usuario_atual():
            if request.path.startswith("/api") or request.method == "POST":
                abort(401)
            return redirect(url_for("entrar"))
        return fn(*a, **kw)
    return wrapper


def confere_csrf():
    tok = request.form.get("csrf") or request.headers.get("X-CSRF")
    if not tok or not secrets.compare_digest(tok, session.get("csrf", "")):
        abort(400)


def ip_cliente():
    return (request.headers.get("X-Real-IP")
            or (request.headers.get("X-Forwarded-For", "").split(",")[0].strip())
            or request.remote_addr or "?")


# --------------------------------------------------------------- PÁGINAS
@app.get("/")
def index():
    db = get_db()
    posts = db.execute("""
        SELECT p.*,
          (SELECT COUNT(*) FROM likes l WHERE l.post_id = p.id) AS likes,
          (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id) AS ncomments,
          EXISTS(SELECT 1 FROM likes l WHERE l.post_id = p.id AND l.visitor = ?) AS liked
        FROM posts p
        ORDER BY p.event_date DESC, p.id DESC
    """, (g.vid,)).fetchall()
    return render_template("index.html", posts=posts)


@app.route("/entrar", methods=["GET", "POST"])
def entrar():
    if usuario_atual():
        return redirect(url_for("index"))
    erro = None
    if request.method == "POST":
        confere_csrf()
        db = get_db()
        ip = ip_cliente()
        agora_ts = time.time()
        db.execute("DELETE FROM login_fail WHERE at < ?", (agora_ts - 900,))
        falhas = db.execute("SELECT COUNT(*) FROM login_fail WHERE ip=?", (ip,)).fetchone()[0]
        if falhas >= 8:
            erro = "Muitas tentativas. Espere uns 15 minutinhos e tente de novo."
        else:
            u = db.execute("SELECT * FROM users WHERE username=?",
                           (request.form.get("usuario", "").strip().lower(),)).fetchone()
            if u and check_password_hash(u["password_hash"], request.form.get("senha", "")):
                session.clear()
                session.permanent = True
                session["uid"] = u["id"]
                db.commit()
                return redirect(url_for("index"))
            db.execute("INSERT INTO login_fail(ip, at) VALUES(?,?)", (ip, agora_ts))
            erro = "Usuário ou senha incorretos."
        db.commit()
    return render_template("entrar.html", erro=erro)


@app.post("/sair")
def sair():
    confere_csrf()
    session.clear()
    return redirect(url_for("index"))


def tipo_por_extensao(nome):
    ext = nome.rsplit(".", 1)[-1].lower() if "." in nome else ""
    if ext in EXT_FOTO:
        return "photo", ext
    if ext in EXT_VIDEO:
        return "video", ext
    return None, ext


def salvar_foto(arquivo, ext):
    """Salva a foto (redimensionada e com a rotação correta) e devolve o nome do arquivo."""
    if ext == "gif" or Image is None:
        nome = uuid.uuid4().hex + "." + ext
        arquivo.save(UPLOADS / nome)
        return nome
    nome = uuid.uuid4().hex + ".jpg"
    img = Image.open(arquivo.stream)
    img = ImageOps.exif_transpose(img)
    img.thumbnail((2000, 2000))
    if img.mode != "RGB":
        img = img.convert("RGB")
    img.save(UPLOADS / nome, "JPEG", quality=86, optimize=True)
    return nome


@app.route("/novo", methods=["GET", "POST"])
@exige_login
def novo():
    if request.method == "GET":
        return render_template("novo.html", hoje=datetime.now().strftime("%Y-%m-%d"))
    confere_csrf()
    ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    def falha(msg):
        if ajax:
            return jsonify(ok=False, erro=msg), 400
        flash(msg)
        return redirect(url_for("novo"))

    modo = request.form.get("modo", "midia")
    titulo = request.form.get("titulo", "").strip()[:120]
    texto = request.form.get("texto", "").strip()[:8000]
    data = request.form.get("data", "").strip()
    try:
        datetime.strptime(data, "%Y-%m-%d")
    except ValueError:
        data = datetime.now().strftime("%Y-%m-%d")

    kind, filename = None, None
    if modo == "cartinha":
        kind = "letter"
        if not texto:
            return falha("Escreva o texto da cartinha. 💌")
    else:
        arq = request.files.get("arquivo")
        if not arq or not arq.filename:
            return falha("Escolha uma foto ou um vídeo.")
        kind, ext = tipo_por_extensao(arq.filename)
        if not kind:
            return falha("Formato não suportado. Use JPG, PNG, WEBP, GIF, MP4, MOV ou WEBM.")
        try:
            if kind == "photo":
                filename = salvar_foto(arq, ext)
            else:
                filename = uuid.uuid4().hex + "." + ext
                arq.save(UPLOADS / filename)
        except Exception:
            return falha("Não consegui ler esse arquivo. Tente outro.")

    db = get_db()
    db.execute(
        "INSERT INTO posts(kind,title,body,filename,event_date,author,created_at) VALUES(?,?,?,?,?,?,?)",
        (kind, titulo, texto, filename, data, usuario_atual()["display_name"], agora()))
    db.commit()
    if ajax:
        return jsonify(ok=True, redirect=url_for("index") + "#momentos")
    return redirect(url_for("index") + "#momentos")


@app.post("/post/<int:pid>/apagar")
@exige_login
def apagar_post(pid):
    confere_csrf()
    db = get_db()
    p = db.execute("SELECT filename FROM posts WHERE id=?", (pid,)).fetchone()
    if not p:
        abort(404)
    db.execute("DELETE FROM posts WHERE id=?", (pid,))
    db.commit()
    if p["filename"]:
        try:
            (UPLOADS / p["filename"]).unlink()
        except FileNotFoundError:
            pass
    return jsonify(ok=True)


@app.get("/midia/<path:nome>")
def midia(nome):
    return send_from_directory(UPLOADS, nome, conditional=True, max_age=60 * 60 * 24 * 365)


# ------------------------------------------------------------------- API
def post_json(db, pid):
    p = db.execute("""
        SELECT p.*,
          (SELECT COUNT(*) FROM likes l WHERE l.post_id = p.id) AS likes,
          EXISTS(SELECT 1 FROM likes l WHERE l.post_id = p.id AND l.visitor = ?) AS liked
        FROM posts p WHERE p.id=?""", (g.vid, pid)).fetchone()
    if not p:
        abort(404)
    com = db.execute("SELECT id,name,text,created_at FROM comments WHERE post_id=? ORDER BY id",
                     (pid,)).fetchall()
    return dict(
        id=p["id"], kind=p["kind"], title=p["title"], body=p["body"],
        url=url_for("midia", nome=p["filename"]) if p["filename"] else None,
        author=p["author"], date=datebr(p["event_date"]),
        likes=p["likes"], liked=bool(p["liked"]),
        can_delete=bool(usuario_atual()),
        comments=[dict(id=c["id"], name=c["name"], text=c["text"], at=c["created_at"]) for c in com])


@app.get("/api/post/<int:pid>")
def api_post(pid):
    return jsonify(post_json(get_db(), pid))


@app.post("/api/post/<int:pid>/like")
def api_like(pid):
    db = get_db()
    if not db.execute("SELECT 1 FROM posts WHERE id=?", (pid,)).fetchone():
        abort(404)
    ja = db.execute("SELECT 1 FROM likes WHERE post_id=? AND visitor=?", (pid, g.vid)).fetchone()
    if ja:
        db.execute("DELETE FROM likes WHERE post_id=? AND visitor=?", (pid, g.vid))
        liked = False
    else:
        db.execute("INSERT INTO likes(post_id,visitor,created_at) VALUES(?,?,?)", (pid, g.vid, agora()))
        liked = True
    db.commit()
    n = db.execute("SELECT COUNT(*) FROM likes WHERE post_id=?", (pid,)).fetchone()[0]
    return jsonify(liked=liked, count=n)


@app.post("/api/post/<int:pid>/comment")
def api_comment(pid):
    db = get_db()
    if not db.execute("SELECT 1 FROM posts WHERE id=?", (pid,)).fetchone():
        abort(404)
    dados = request.get_json(silent=True) or {}
    nome = str(dados.get("name", "")).strip()[:40]
    texto = str(dados.get("text", "")).strip()[:400]
    if not nome or not texto:
        return jsonify(erro="Preencha seu nome e o comentário."), 400
    recentes = db.execute(
        "SELECT COUNT(*) FROM comments WHERE visitor=? AND created_at > ?",
        (g.vid, datetime.fromtimestamp(datetime.now().timestamp() - 600, timezone.utc)
         .isoformat(timespec="seconds").replace("+00:00", "Z"))).fetchone()[0]
    if recentes >= 6:
        return jsonify(erro="Calma! Muitos comentários seguidos. Tente daqui a pouco. 💕"), 429
    cur = db.execute("INSERT INTO comments(post_id,visitor,name,text,created_at) VALUES(?,?,?,?,?)",
                     (pid, g.vid, nome, texto, agora()))
    db.commit()
    n = db.execute("SELECT COUNT(*) FROM comments WHERE post_id=?", (pid,)).fetchone()[0]
    return jsonify(comment=dict(id=cur.lastrowid, name=nome, text=texto, at=agora()), count=n)


@app.post("/api/comment/<int:cid>/apagar")
@exige_login
def api_apagar_comentario(cid):
    confere_csrf()
    db = get_db()
    c = db.execute("SELECT post_id FROM comments WHERE id=?", (cid,)).fetchone()
    if not c:
        abort(404)
    db.execute("DELETE FROM comments WHERE id=?", (cid,))
    db.commit()
    n = db.execute("SELECT COUNT(*) FROM comments WHERE post_id=?", (c["post_id"],)).fetchone()[0]
    return jsonify(ok=True, count=n)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
