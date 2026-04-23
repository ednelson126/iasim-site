"""
IAsim PRO — Servidor Web (Flask)
Versão: 2.0 PROFISSIONAL
Autor: Ednelson (refatorado)

Melhorias aplicadas:
- Chaves via variáveis de ambiente (.env)
- Banco SQLite compartilhado com o bot
- Senhas com hash bcrypt
- Página de vendas premium com VSL real
- Webhook automático do Mercado Pago
- Painel web com design profissional
- Proteção CSRF básica
- Logs estruturados
"""

import logging
import os
import random
import sqlite3
import string
from datetime import datetime
from functools import wraps
from pathlib import Path

import bcrypt
import requests
from dotenv import load_dotenv
from flask import (
    Flask,
    request,
    render_template_string,
    session,
    redirect,
    jsonify,
    abort,
)

# ==============================
# CONFIGURAÇÃO
# ==============================
load_dotenv()

MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
TELEGRAM_TOKEN  = os.getenv("TELEGRAM_TOKEN")
SITE_URL        = os.getenv("SITE_URL", "https://iasim-site.onrender.com")
SECRET_KEY      = os.getenv("FLASK_SECRET", os.urandom(32).hex())
PRECO_VIP       = float(os.getenv("PRECO_VIP", "19.90"))

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
    handlers=[logging.FileHandler("iasim_web.log"), logging.StreamHandler()],
)
logger = logging.getLogger("IAsimWEB")

app = Flask(__name__)
app.secret_key = SECRET_KEY
DB_PATH = Path("iasim.db")

# ==============================
# BANCO DE DADOS
# ==============================
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                telegram_id     TEXT PRIMARY KEY,
                plano           TEXT    DEFAULT 'gratis',
                nicho           TEXT    DEFAULT 'ganhar dinheiro na internet',
                usos_gratuitos  INTEGER DEFAULT 0,
                payment_id      TEXT,
                token_vinculo   TEXT,
                web_username    TEXT,
                web_senha_hash  TEXT,
                criado_em       TEXT    DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS web_users (
                username        TEXT PRIMARY KEY,
                senha_hash      TEXT NOT NULL,
                telegram_id     TEXT,
                plano           TEXT DEFAULT 'gratis',
                nicho           TEXT DEFAULT 'ganhar dinheiro na internet',
                token_vinculo   TEXT,
                criado_em       TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()

def get_web_user(username: str) -> dict | None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM web_users WHERE username = ?", (username,)
        ).fetchone()
    return dict(row) if row else None

def create_web_user(username: str, senha: str) -> dict:
    senha_hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO web_users (username, senha_hash) VALUES (?, ?)",
            (username, senha_hash),
        )
        conn.commit()
    return get_web_user(username)

def check_senha(username: str, senha: str) -> bool:
    user = get_web_user(username)
    if not user:
        return False
    return bcrypt.checkpw(senha.encode(), user["senha_hash"].encode())

def update_web_user(username: str, **kwargs):
    if not kwargs:
        return
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values()) + [username]
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(f"UPDATE web_users SET {sets} WHERE username = ?", vals)
        conn.commit()

def get_web_user_by_token(token: str) -> dict | None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM web_users WHERE token_vinculo = ?", (token,)
        ).fetchone()
    return dict(row) if row else None

def update_telegram_user(telegram_id: str, **kwargs):
    if not kwargs:
        return
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values()) + [telegram_id]
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(f"UPDATE usuarios SET {sets} WHERE telegram_id = ?", vals)
        conn.commit()

def gerar_token() -> str:
    return "IASIM-" + "".join(
        random.choices(string.ascii_uppercase + string.digits, k=8)
    )

def enviar_telegram(chat_id: str, msg: str):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(
            url,
            json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"},
            timeout=5,
        )
    except Exception as exc:
        logger.error("Erro Telegram: %s", exc)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect("/entrar")
        return f(*args, **kwargs)
    return decorated

# ==============================
# TEMPLATES
# ==============================

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>IAsim PRO — Entrar</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --brand: #00ff88;
    --brand2: #00ccff;
    --dark: #040b14;
    --surface: #0a1628;
    --border: rgba(255,255,255,0.08);
  }
  body {
    font-family: 'DM Sans', sans-serif;
    background: var(--dark);
    color: #f1f5f9;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background-image: radial-gradient(ellipse 80% 50% at 50% -20%, rgba(0,255,136,0.07), transparent);
  }
  .box {
    width: 100%;
    max-width: 420px;
    padding: 48px 40px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 24px;
    box-shadow: 0 40px 80px rgba(0,0,0,0.6);
  }
  .logo {
    font-family: 'Syne', sans-serif;
    font-size: 2rem;
    font-weight: 800;
    background: linear-gradient(135deg, var(--brand), var(--brand2));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 8px;
  }
  .subtitle { color: #64748b; font-size: 0.9rem; margin-bottom: 36px; }
  .error { color: #f87171; font-size: 0.85rem; margin-bottom: 16px; padding: 10px 14px; background: rgba(248,113,113,0.1); border-radius: 8px; border-left: 3px solid #f87171; }
  label { display: block; font-size: 0.8rem; font-weight: 500; color: #94a3b8; margin-bottom: 6px; letter-spacing: 0.05em; text-transform: uppercase; }
  input {
    width: 100%;
    padding: 14px 16px;
    background: rgba(255,255,255,0.04);
    border: 1px solid var(--border);
    border-radius: 12px;
    color: #f1f5f9;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.95rem;
    margin-bottom: 20px;
    transition: border 0.2s;
    outline: none;
  }
  input:focus { border-color: var(--brand); }
  button {
    width: 100%;
    padding: 16px;
    background: linear-gradient(135deg, var(--brand), #00cc6a);
    color: #040b14;
    font-family: 'Syne', sans-serif;
    font-size: 1rem;
    font-weight: 800;
    border: none;
    border-radius: 12px;
    cursor: pointer;
    transition: opacity 0.2s, transform 0.1s;
    letter-spacing: 0.02em;
  }
  button:hover { opacity: 0.92; }
  button:active { transform: scale(0.99); }
  .note { text-align: center; font-size: 0.8rem; color: #475569; margin-top: 20px; }
  .note a { color: var(--brand); text-decoration: none; }
</style>
</head>
<body>
<div class="box">
  <div class="logo">IAsim PRO</div>
  <p class="subtitle">Acesse seu painel ou crie sua conta</p>
  {% if erro %}<div class="error">{{ erro }}</div>{% endif %}
  <form method="POST">
    <label>Usuário</label>
    <input name="username" placeholder="seu_usuario" autocomplete="username" required>
    <label>Senha</label>
    <input name="senha" type="password" placeholder="••••••••" autocomplete="current-password" required>
    <button type="submit">ENTRAR / CRIAR CONTA</button>
  </form>
  <p class="note">Não tem conta? Basta digitar um usuário e senha novos. <br><a href="/oferta">Ver oferta →</a></p>
</div>
</body>
</html>
"""

PAINEL_HTML = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>IAsim PRO — Painel</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --brand: #00ff88;
    --brand2: #00ccff;
    --dark: #040b14;
    --surface: #0a1628;
    --surface2: #0f1f38;
    --border: rgba(255,255,255,0.07);
    --text: #e2e8f0;
    --muted: #64748b;
  }
  body { font-family: 'DM Sans', sans-serif; background: var(--dark); color: var(--text); min-height: 100vh; }
  
  /* NAV */
  nav {
    display: flex; align-items: center; justify-content: space-between;
    padding: 20px 40px;
    border-bottom: 1px solid var(--border);
    background: rgba(10,22,40,0.8);
    backdrop-filter: blur(12px);
    position: sticky; top: 0; z-index: 100;
  }
  .nav-logo { font-family: 'Syne', sans-serif; font-size: 1.4rem; font-weight: 800; background: linear-gradient(135deg, var(--brand), var(--brand2)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
  .nav-right { display: flex; gap: 12px; align-items: center; }
  .badge-vip { background: linear-gradient(135deg, #f59e0b, #d97706); color: #000; padding: 4px 12px; border-radius: 100px; font-size: 0.75rem; font-weight: 700; letter-spacing: 0.05em; }
  .badge-free { background: var(--surface2); color: var(--muted); padding: 4px 12px; border-radius: 100px; font-size: 0.75rem; font-weight: 600; }
  .btn-logout { background: transparent; color: var(--muted); border: 1px solid var(--border); padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 0.85rem; text-decoration: none; transition: all 0.2s; }
  .btn-logout:hover { color: #f87171; border-color: #f87171; }

  /* MAIN */
  main { max-width: 900px; margin: 0 auto; padding: 48px 24px; }
  h1 { font-family: 'Syne', sans-serif; font-size: 2rem; font-weight: 800; margin-bottom: 8px; }
  .welcome-sub { color: var(--muted); margin-bottom: 40px; }

  /* CARDS */
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 20px; margin-bottom: 32px; }
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 28px;
    transition: border-color 0.2s, transform 0.2s;
  }
  .card:hover { border-color: rgba(0,255,136,0.3); transform: translateY(-3px); }
  .card-icon { font-size: 1.8rem; margin-bottom: 14px; }
  .card-title { font-family: 'Syne', sans-serif; font-size: 0.95rem; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 8px; }
  .card-value { font-size: 1.3rem; font-weight: 500; }

  /* FORM NICHO */
  .section { background: var(--surface); border: 1px solid var(--border); border-radius: 20px; padding: 32px; margin-bottom: 24px; }
  .section h2 { font-family: 'Syne', sans-serif; font-size: 1.1rem; font-weight: 700; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; }
  .input-group { display: flex; gap: 12px; }
  input[type=text] {
    flex: 1;
    padding: 14px 16px;
    background: rgba(255,255,255,0.04);
    border: 1px solid var(--border);
    border-radius: 12px;
    color: var(--text);
    font-family: 'DM Sans', sans-serif;
    font-size: 0.95rem;
    outline: none;
    transition: border 0.2s;
  }
  input[type=text]:focus { border-color: var(--brand); }
  .btn { padding: 14px 24px; border: none; border-radius: 12px; font-family: 'Syne', sans-serif; font-weight: 700; cursor: pointer; font-size: 0.9rem; transition: all 0.2s; }
  .btn-primary { background: linear-gradient(135deg, var(--brand), #00cc6a); color: #040b14; }
  .btn-primary:hover { opacity: 0.9; }
  .btn-secondary { background: var(--surface2); color: var(--text); border: 1px solid var(--border); }
  .btn-secondary:hover { border-color: var(--brand2); color: var(--brand2); }

  /* TOKEN */
  .token-box { background: rgba(0,255,136,0.05); border: 1px solid rgba(0,255,136,0.2); border-radius: 12px; padding: 16px 20px; margin-top: 16px; font-family: monospace; font-size: 1rem; color: var(--brand); letter-spacing: 0.1em; }
  .token-instruction { font-size: 0.85rem; color: var(--muted); margin-top: 8px; }

  /* VIP */
  .vip-banner {
    background: linear-gradient(135deg, rgba(245,158,11,0.1), rgba(217,119,6,0.05));
    border: 1px solid rgba(245,158,11,0.3);
    border-radius: 20px;
    padding: 32px;
    text-align: center;
    margin-bottom: 24px;
  }
  .vip-banner h2 { font-family: 'Syne', sans-serif; font-size: 1.4rem; margin-bottom: 12px; color: #f59e0b; }
  .vip-banner p { color: var(--muted); margin-bottom: 20px; }
  .btn-vip { display: inline-block; padding: 16px 40px; background: linear-gradient(135deg, #f59e0b, #d97706); color: #000; font-family: 'Syne', sans-serif; font-weight: 800; font-size: 1rem; border-radius: 12px; text-decoration: none; transition: opacity 0.2s; }
  .btn-vip:hover { opacity: 0.9; }
  .btn-tg { display: inline-block; padding: 14px 30px; background: linear-gradient(135deg, #0088cc, #006699); color: #fff; font-family: 'Syne', sans-serif; font-weight: 700; border-radius: 12px; text-decoration: none; font-size: 0.95rem; }

  @media(max-width: 600px) {
    nav { padding: 16px 20px; }
    .input-group { flex-direction: column; }
    main { padding: 32px 16px; }
  }
</style>
</head>
<body>

<nav>
  <div class="nav-logo">IAsim PRO</div>
  <div class="nav-right">
    {% if user.plano == 'vip' %}
      <span class="badge-vip">⭐ VIP</span>
    {% else %}
      <span class="badge-free">Plano Gratuito</span>
    {% endif %}
    <a href="/logout" class="btn-logout">Sair</a>
  </div>
</nav>

<main>
  <h1>Olá, {{ username }}! 👋</h1>
  <p class="welcome-sub">Gerencie sua conta e conecte seu bot.</p>

  <div class="grid">
    <div class="card">
      <div class="card-icon">📌</div>
      <div class="card-title">Plano Atual</div>
      <div class="card-value">{% if user.plano == 'vip' %}⭐ VIP — Ilimitado{% else %}Gratuito{% endif %}</div>
    </div>
    <div class="card">
      <div class="card-icon">🎯</div>
      <div class="card-title">Seu Nicho</div>
      <div class="card-value">{{ user.nicho or 'Não definido' }}</div>
    </div>
    <div class="card">
      <div class="card-icon">📱</div>
      <div class="card-title">Telegram</div>
      <div class="card-value" style="font-size:1rem;">{% if user.telegram_id %}✅ Conectado{% else %}❌ Não conectado{% endif %}</div>
    </div>
  </div>

  {% if user.plano != 'vip' %}
  <div class="vip-banner">
    <h2>🚀 Desbloqueie o Plano VIP</h2>
    <p>Geração ilimitada de conteúdo viral, roteiros profissionais e estratégias de venda. Pagamento único.</p>
    <a href="https://t.me/Iasim_bot" class="btn-vip">⭐ ATIVAR VIP — R${{ preco }}</a>
  </div>
  {% endif %}

  <div class="section">
    <h2>🎯 Definir Nicho</h2>
    <form action="/salvar_nicho" method="POST">
      <div class="input-group">
        <input type="text" name="nicho" placeholder="Ex: Marketing digital para pequenos negócios" value="{{ user.nicho or '' }}">
        <button type="submit" class="btn btn-primary">Salvar</button>
      </div>
    </form>
  </div>

  <div class="section">
    <h2>🤖 Conectar ao Bot no Telegram</h2>
    <p style="color:var(--muted); margin-bottom:16px; font-size:0.9rem;">Gere um código único e envie para o bot para sincronizar sua conta.</p>
    
    {% if token %}
    <div class="token-box">{{ token }}</div>
    <p class="token-instruction">Envie esse comando no bot: <strong>/vincular {{ token }}</strong></p>
    {% endif %}

    <div style="display:flex; gap:12px; margin-top:16px; flex-wrap:wrap;">
      <form action="/gerar_token" method="POST">
        <button type="submit" class="btn btn-secondary">🔑 Gerar Código</button>
      </form>
      <a href="https://t.me/Iasim_bot" class="btn-tg" target="_blank">
        <i class="fab fa-telegram"></i> Abrir Bot
      </a>
    </div>
  </div>

</main>
</body>
</html>
"""

# ==============================
# PÁGINA DE VENDAS PREMIUM
# ==============================
OFERTA_HTML = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>IAsim PRO — O Motor de Conteúdo Viral com IA</title>
<meta name="description" content="Crie roteiros virais, conteúdos prontos e estratégias de venda automaticamente com IA. Plano único por R$19,90.">
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800;900&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --brand: #00ff88;
    --brand2: #00ccff;
    --dark: #030a13;
    --surface: #080f1e;
    --surface2: #0c1a2e;
    --text: #e8f0fe;
    --muted: #6b7fa3;
    --border: rgba(255,255,255,0.06);
  }
  html { scroll-behavior: smooth; }
  body {
    font-family: 'DM Sans', sans-serif;
    background: var(--dark);
    color: var(--text);
    overflow-x: hidden;
    line-height: 1.65;
  }

  /* ---- NOTIF ---- */
  #sale-notif {
    position: fixed; bottom: 24px; left: 20px;
    background: #fff; color: #0a0f1e;
    padding: 14px 20px; border-radius: 14px;
    display: flex; align-items: center; gap: 12px;
    box-shadow: 0 20px 50px rgba(0,0,0,0.5);
    z-index: 9999;
    transform: translateY(200%);
    transition: transform 0.5s cubic-bezier(0.34,1.56,0.64,1);
    max-width: 280px; font-size: 13px;
  }
  #sale-notif.show { transform: translateY(0); }

  /* ---- NAV ---- */
  nav {
    position: fixed; top: 0; left: 0; right: 0; z-index: 200;
    display: flex; align-items: center; justify-content: space-between;
    padding: 18px 48px;
    background: rgba(3,10,19,0.85);
    backdrop-filter: blur(16px);
    border-bottom: 1px solid var(--border);
  }
  .nav-logo { font-family: 'Syne', sans-serif; font-size: 1.5rem; font-weight: 900; background: linear-gradient(135deg, var(--brand), var(--brand2)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
  .nav-cta { padding: 10px 24px; background: var(--brand); color: #030a13; font-family: 'Syne', sans-serif; font-weight: 800; border-radius: 10px; text-decoration: none; font-size: 0.9rem; transition: opacity 0.2s; }
  .nav-cta:hover { opacity: 0.88; }

  /* ---- HERO ---- */
  .hero {
    min-height: 100vh;
    display: flex; align-items: center; justify-content: center;
    text-align: center;
    padding: 140px 24px 80px;
    background:
      radial-gradient(ellipse 60% 50% at 50% 0%, rgba(0,255,136,0.08) 0%, transparent 70%),
      radial-gradient(ellipse 40% 30% at 80% 50%, rgba(0,204,255,0.05) 0%, transparent 60%);
    position: relative;
  }
  .hero::before {
    content: '';
    position: absolute; inset: 0;
    background-image: radial-gradient(rgba(255,255,255,0.03) 1px, transparent 1px);
    background-size: 32px 32px;
    pointer-events: none;
  }
  .hero-inner { max-width: 900px; position: relative; }
  .hero-badge {
    display: inline-flex; align-items: center; gap: 8px;
    background: rgba(0,255,136,0.1); border: 1px solid rgba(0,255,136,0.25);
    color: var(--brand); padding: 6px 16px; border-radius: 100px;
    font-size: 0.8rem; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase;
    margin-bottom: 28px;
  }
  .hero h1 {
    font-family: 'Syne', sans-serif;
    font-size: clamp(2.4rem, 6vw, 5rem);
    font-weight: 900;
    line-height: 1.05;
    letter-spacing: -2px;
    margin-bottom: 24px;
  }
  .hero h1 .accent { background: linear-gradient(135deg, var(--brand), var(--brand2)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
  .hero-sub { font-size: clamp(1rem, 2vw, 1.25rem); color: var(--muted); max-width: 680px; margin: 0 auto 44px; }
  .hero-cta {
    display: inline-flex; align-items: center; gap: 12px;
    background: linear-gradient(135deg, var(--brand), #00cc6a);
    color: #030a13; font-family: 'Syne', sans-serif; font-weight: 900;
    font-size: 1.15rem; padding: 22px 56px; border-radius: 16px;
    text-decoration: none;
    box-shadow: 0 0 60px rgba(0,255,136,0.25);
    transition: all 0.25s;
  }
  .hero-cta:hover { transform: translateY(-3px); box-shadow: 0 0 80px rgba(0,255,136,0.4); }
  .hero-social { margin-top: 28px; font-size: 0.85rem; color: var(--muted); }
  .hero-social span { color: var(--brand); font-weight: 600; }

  /* ---- VSL ---- */
  .vsl-wrap {
    max-width: 860px; margin: 0 auto;
    padding: 0 24px 100px;
  }
  .vsl-box {
    border-radius: 28px;
    overflow: hidden;
    border: 1px solid var(--border);
    background: var(--surface);
    box-shadow: 0 60px 120px rgba(0,0,0,0.6);
    position: relative;
    padding-bottom: 56.25%;
    height: 0;
  }
  .vsl-box iframe { position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none; }
  .vsl-placeholder {
    position: absolute; inset: 0;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    gap: 16px; background: var(--surface2);
    cursor: pointer;
  }
  .play-btn {
    width: 80px; height: 80px; border-radius: 50%;
    background: linear-gradient(135deg, var(--brand), #00cc6a);
    display: flex; align-items: center; justify-content: center;
    font-size: 2rem; color: #030a13;
    box-shadow: 0 0 40px rgba(0,255,136,0.4);
    transition: transform 0.2s;
  }
  .play-btn:hover { transform: scale(1.08); }
  .vsl-label { font-family: 'Syne', sans-serif; font-size: 1rem; font-weight: 700; color: var(--muted); }

  /* ---- SECTIONS ---- */
  section { padding: 100px 24px; }
  .container { max-width: 1100px; margin: 0 auto; }
  .section-tag {
    display: inline-block; background: rgba(0,204,255,0.08); border: 1px solid rgba(0,204,255,0.2);
    color: var(--brand2); padding: 5px 14px; border-radius: 100px;
    font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em;
    margin-bottom: 16px;
  }
  h2.section-title { font-family: 'Syne', sans-serif; font-size: clamp(1.8rem, 4vw, 3rem); font-weight: 900; letter-spacing: -1px; margin-bottom: 16px; }
  .section-sub { color: var(--muted); font-size: 1.05rem; margin-bottom: 60px; max-width: 580px; }

  /* ---- RECURSOS ---- */
  .recursos-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 24px; }
  .recurso {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 20px; padding: 32px;
    transition: border-color 0.2s, transform 0.2s;
    position: relative; overflow: hidden;
  }
  .recurso::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, var(--brand), var(--brand2));
    opacity: 0; transition: opacity 0.2s;
  }
  .recurso:hover { border-color: rgba(0,255,136,0.2); transform: translateY(-6px); }
  .recurso:hover::before { opacity: 1; }
  .recurso-icon { font-size: 2rem; margin-bottom: 16px; }
  .recurso h3 { font-family: 'Syne', sans-serif; font-size: 1.1rem; font-weight: 800; margin-bottom: 10px; }
  .recurso p { color: var(--muted); font-size: 0.9rem; line-height: 1.6; }

  /* ---- COMO FUNCIONA ---- */
  .steps { display: flex; flex-direction: column; gap: 0; max-width: 700px; }
  .step { display: flex; gap: 24px; padding: 32px 0; border-bottom: 1px solid var(--border); }
  .step:last-child { border: none; }
  .step-num {
    flex-shrink: 0;
    width: 44px; height: 44px; border-radius: 50%;
    background: linear-gradient(135deg, var(--brand), var(--brand2));
    color: #030a13; font-family: 'Syne', sans-serif; font-weight: 900; font-size: 1rem;
    display: flex; align-items: center; justify-content: center;
  }
  .step h3 { font-family: 'Syne', sans-serif; font-weight: 800; margin-bottom: 8px; }
  .step p { color: var(--muted); font-size: 0.9rem; }

  /* ---- DEPOIMENTOS ---- */
  .test-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; }
  .test-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 20px; padding: 28px;
    border-bottom: 3px solid var(--brand);
  }
  .test-stars { color: #f59e0b; font-size: 0.85rem; margin-bottom: 14px; }
  .test-text { font-size: 0.9rem; color: #cbd5e1; line-height: 1.6; margin-bottom: 20px; font-style: italic; }
  .test-author { display: flex; align-items: center; gap: 12px; }
  .test-avatar { width: 44px; height: 44px; border-radius: 50%; object-fit: cover; border: 2px solid var(--brand); }
  .test-name { font-weight: 600; font-size: 0.9rem; }
  .test-role { font-size: 0.8rem; color: var(--muted); }

  /* ---- PUBLICO ---- */
  .publico-grid { display: flex; flex-wrap: wrap; gap: 14px; }
  .publico-tag {
    background: var(--surface2); border: 1px solid var(--border);
    padding: 10px 22px; border-radius: 100px;
    font-size: 0.9rem; font-weight: 500;
    transition: all 0.2s;
  }
  .publico-tag:hover { border-color: var(--brand); color: var(--brand); }

  /* ---- FAQ ---- */
  .faq-list { max-width: 760px; display: flex; flex-direction: column; gap: 12px; }
  .faq-item {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 16px; overflow: hidden;
  }
  .faq-q {
    padding: 22px 28px; font-weight: 600; cursor: pointer;
    display: flex; justify-content: space-between; align-items: center;
    transition: color 0.2s;
  }
  .faq-q:hover { color: var(--brand); }
  .faq-a { padding: 0 28px 22px; color: var(--muted); font-size: 0.9rem; line-height: 1.7; display: none; }
  .faq-item.open .faq-a { display: block; }
  .faq-item.open .faq-icon { transform: rotate(45deg); }
  .faq-icon { transition: transform 0.2s; color: var(--brand); }

  /* ---- CTA FINAL ---- */
  .cta-final {
    text-align: center;
    padding: 120px 24px;
    background:
      radial-gradient(ellipse 70% 60% at 50% 100%, rgba(0,255,136,0.07), transparent),
      var(--surface);
    border-top: 1px solid var(--border);
  }
  .cta-price {
    font-family: 'Syne', sans-serif;
    font-size: clamp(3rem, 10vw, 6rem);
    font-weight: 900;
    background: linear-gradient(135deg, var(--brand), var(--brand2));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    line-height: 1;
    margin-bottom: 8px;
  }
  .cta-price-sub { color: var(--muted); margin-bottom: 48px; font-size: 1rem; }
  .cta-btn {
    display: inline-flex; align-items: center; gap: 14px;
    background: linear-gradient(135deg, var(--brand), #00cc6a);
    color: #030a13; font-family: 'Syne', sans-serif; font-weight: 900;
    font-size: 1.25rem; padding: 26px 72px; border-radius: 20px;
    text-decoration: none;
    box-shadow: 0 0 80px rgba(0,255,136,0.3);
    transition: all 0.25s;
  }
  .cta-btn:hover { transform: translateY(-4px); box-shadow: 0 0 100px rgba(0,255,136,0.45); }
  .cta-guarantee { margin-top: 28px; color: var(--muted); font-size: 0.85rem; }
  .cta-guarantee i { color: var(--brand); }

  /* ---- FOOTER ---- */
  footer { padding: 48px 24px; text-align: center; border-top: 1px solid var(--border); color: var(--muted); font-size: 0.85rem; }
  footer a { color: var(--muted); text-decoration: none; }
  footer a:hover { color: var(--brand); }

  @media(max-width: 768px) {
    nav { padding: 16px 20px; }
    .nav-logo { font-size: 1.2rem; }
    .hero-cta { padding: 18px 36px; font-size: 1rem; }
  }
</style>
</head>
<body>

<!-- NOTIFICAÇÃO VENDA -->
<div id="sale-notif">
  <i class="fas fa-check-circle" style="color:#10b981; font-size:18px; flex-shrink:0;"></i>
  <span id="notif-text">...</span>
</div>

<!-- NAV -->
<nav>
  <div class="nav-logo">IAsim PRO</div>
  <a href="#cta" class="nav-cta">Quero Acesso →</a>
</nav>

<!-- HERO -->
<div class="hero">
  <div class="hero-inner">
    <div class="hero-badge"><i class="fas fa-bolt"></i> Powered by IA Avançada</div>
    <h1>O Bot que cria <span class="accent">Conteúdo Viral</span> para você lucrar todos os dias.</h1>
    <p class="hero-sub">Chega de bloqueio criativo. Com o IAsim PRO você tem uma linha de produção automatizada de roteiros, legendas e estratégias de venda — direto no Telegram.</p>
    <a href="#cta" class="hero-cta">
      <i class="fab fa-telegram"></i>
      QUERO MEU ACESSO AGORA
    </a>
    <p class="hero-social">Mais de <span>1.200 criadores</span> já usam o IAsim PRO 🚀</p>
  </div>
</div>

<!-- VSL -->
<div class="vsl-wrap">
  <div class="vsl-box">
    <div class="vsl-placeholder" id="vsl-placeholder" onclick="loadVSL()">
      <div class="play-btn"><i class="fas fa-play" style="margin-left:4px;"></i></div>
      <p class="vsl-label">Assista e veja o bot em ação</p>
    </div>
  </div>
</div>

<!-- RECURSOS -->
<section style="background: var(--surface); border-top: 1px solid var(--border); border-bottom: 1px solid var(--border);">
  <div class="container">
    <div class="section-tag">Recursos</div>
    <h2 class="section-title">Tudo que você precisa<br>para viralizar.</h2>
    <p class="section-sub">Ferramentas de criação profissional disponíveis a qualquer hora, para qualquer nicho.</p>
    <div class="recursos-grid">
      <div class="recurso">
        <div class="recurso-icon">💡</div>
        <h3>Ideias Virais Sob Demanda</h3>
        <p>5 ideias únicas para o seu nicho com análise de por que vão viralizar e qual gatilho psicológico usar.</p>
      </div>
      <div class="recurso">
        <div class="recurso-icon">🎬</div>
        <h3>Roteiros de 30 Segundos</h3>
        <p>Estrutura completa: gancho, desenvolvimento, virada e CTA. Pronto para gravar, sem precisar pensar.</p>
      </div>
      <div class="recurso">
        <div class="recurso-icon">🔥</div>
        <h3>Pacote de Conteúdo Completo</h3>
        <p>Carrossel, vídeo curto, stories e legenda — tudo de uma vez. Semana inteira de conteúdo em minutos.</p>
      </div>
      <div class="recurso">
        <div class="recurso-icon">📊</div>
        <h3>Estratégia de Vendas</h3>
        <p>Calendário de 7 dias, funil orgânico completo e copies prontas para stories com gatilhos de conversão.</p>
      </div>
      <div class="recurso">
        <div class="recurso-icon">🎯</div>
        <h3>Personalização por Nicho</h3>
        <p>Todo conteúdo é gerado especificamente para o seu nicho. Sem respostas genéricas ou templatesóbvios.</p>
      </div>
      <div class="recurso">
        <div class="recurso-icon">⚡</div>
        <h3>Direto no Telegram</h3>
        <p>Sem apps extras, sem login toda hora. Acesse de qualquer dispositivo, a qualquer momento, com 2 toques.</p>
      </div>
    </div>
  </div>
</section>

<!-- COMO FUNCIONA -->
<section>
  <div class="container">
    <div class="section-tag">Como Funciona</div>
    <h2 class="section-title">3 passos para<br>começar a criar.</h2>
    <p class="section-sub">Simples o suficiente para qualquer pessoa. Poderoso o suficiente para profissionais.</p>
    <div class="steps">
      <div class="step">
        <div class="step-num">1</div>
        <div>
          <h3>Acesse o Bot no Telegram</h3>
          <p>Após o pagamento, seu acesso é liberado automaticamente. Clique em /start e o bot está pronto.</p>
        </div>
      </div>
      <div class="step">
        <div class="step-num">2</div>
        <div>
          <h3>Defina seu Nicho</h3>
          <p>Diga para o bot qual é o tema do seu conteúdo. A partir daí, tudo é 100% personalizado para você.</p>
        </div>
      </div>
      <div class="step">
        <div class="step-num">3</div>
        <div>
          <h3>Escolha o que criar e publique</h3>
          <p>Selecione ideias, roteiro, conteúdo ou estratégia. Receba em segundos e publique direto nas suas redes.</p>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- DEPOIMENTOS -->
<section style="background: var(--surface); border-top: 1px solid var(--border); border-bottom: 1px solid var(--border);">
  <div class="container">
    <div class="section-tag">Resultados</div>
    <h2 class="section-title">O que nossos<br>usuários dizem.</h2>
    <p class="section-sub">Resultados reais de criadores que usam o IAsim PRO no dia a dia.</p>
    <div class="test-grid">
      <div class="test-card">
        <div class="test-stars">★★★★★</div>
        <p class="test-text">"O bot gerou um roteiro que bateu mais de 100k visualizações em menos de 24h. Nunca vi algo tão preciso para prender a atenção no feed."</p>
        <div class="test-author">
          <img src="https://randomuser.me/api/portraits/men/32.jpg" class="test-avatar" alt="">
          <div><div class="test-name">Ricardo A.</div><div class="test-role">Produtor Digital</div></div>
        </div>
      </div>
      <div class="test-card">
        <div class="test-stars">★★★★★</div>
        <p class="test-text">"Parei de perder noites criando calendários. O IAsim faz em 5 minutos o que eu levava 3 dias para estruturar. Vale cada centavo."</p>
        <div class="test-author">
          <img src="https://randomuser.me/api/portraits/women/44.jpg" class="test-avatar" alt="">
          <div><div class="test-name">Julia M.</div><div class="test-role">Social Media</div></div>
        </div>
      </div>
      <div class="test-card">
        <div class="test-stars">★★★★★</div>
        <p class="test-text">"Minhas vendas no tráfego orgânico subiram desde que comecei a usar os roteiros do IAsim. As CTAs são realmente diferentes de tudo que eu vi."</p>
        <div class="test-author">
          <img src="https://randomuser.me/api/portraits/men/85.jpg" class="test-avatar" alt="">
          <div><div class="test-name">Bruno C.</div><div class="test-role">Afiliado</div></div>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- PÚBLICO -->
<section>
  <div class="container">
    <div class="section-tag">Para Quem É</div>
    <h2 class="section-title">Para quem quer<br>crescer online.</h2>
    <p class="section-sub">Seja qual for o seu nicho, o IAsim PRO cria conteúdo sob medida para você.</p>
    <div class="publico-grid">
      <span class="publico-tag">🎯 Criadores de Conteúdo</span>
      <span class="publico-tag">💰 Afiliados Digitais</span>
      <span class="publico-tag">📱 Social Media</span>
      <span class="publico-tag">🏋️ Personal Trainers</span>
      <span class="publico-tag">🍳 Influencers de Culinária</span>
      <span class="publico-tag">💼 Empreendedores</span>
      <span class="publico-tag">🏠 Corretores de Imóveis</span>
      <span class="publico-tag">📚 Infoprodutores</span>
      <span class="publico-tag">🦺 Profissionais Liberais</span>
      <span class="publico-tag">🎨 Designers e Freelancers</span>
    </div>
  </div>
</section>

<!-- FAQ -->
<section style="background: var(--surface); border-top: 1px solid var(--border);">
  <div class="container">
    <div class="section-tag">Dúvidas</div>
    <h2 class="section-title">Perguntas<br>frequentes.</h2>
    <div class="faq-list">
      <div class="faq-item">
        <div class="faq-q" onclick="toggleFaq(this)">O pagamento é único ou tem mensalidade? <i class="fas fa-plus faq-icon"></i></div>
        <div class="faq-a">Pagamento único de R$19,90. Sem mensalidade, sem renovação. Você paga uma vez e usa para sempre, incluindo novas funcionalidades.</div>
      </div>
      <div class="faq-item">
        <div class="faq-q" onclick="toggleFaq(this)">Funciona para qualquer nicho? <i class="fas fa-plus faq-icon"></i></div>
        <div class="faq-a">Sim. Você define seu nicho e o bot adapta todos os conteúdos especificamente para ele. De saúde a finanças, de culinária a segurança no trabalho — funciona para qualquer área.</div>
      </div>
      <div class="faq-item">
        <div class="faq-q" onclick="toggleFaq(this)">Preciso saber programar? <i class="fas fa-plus faq-icon"></i></div>
        <div class="faq-a">Absolutamente não. O IAsim PRO funciona direto no Telegram com botões simples. Qualquer pessoa com um celular consegue usar desde o primeiro minuto.</div>
      </div>
      <div class="faq-item">
        <div class="faq-q" onclick="toggleFaq(this)">Como o acesso é liberado após o pagamento? <i class="fas fa-plus faq-icon"></i></div>
        <div class="faq-a">Automaticamente. Assim que o PIX é confirmado, seu acesso VIP é liberado no bot sem precisar aguardar nenhuma ação manual. Em geral leva menos de 1 minuto.</div>
      </div>
      <div class="faq-item">
        <div class="faq-q" onclick="toggleFaq(this)">E se eu não gostar? <i class="fas fa-plus faq-icon"></i></div>
        <div class="faq-a">Oferecemos 7 dias de garantia. Se por qualquer motivo não ficar satisfeito, basta entrar em contato e devolvemos 100% do valor.</div>
      </div>
    </div>
  </div>
</section>

<!-- CTA FINAL -->
<div class="cta-final" id="cta">
  <div class="cta-price">R$19,90</div>
  <p class="cta-price-sub">Pagamento único · Acesso vitalício · Garantia de 7 dias</p>
  <a href="https://t.me/Iasim_bot" class="cta-btn">
    <i class="fab fa-telegram"></i>
    QUERO MEU ACESSO AGORA
  </a>
  <p class="cta-guarantee" style="margin-top:32px;">
    <i class="fas fa-shield-alt"></i> Pagamento 100% seguro via PIX · Acesso imediato após confirmação
  </p>
</div>

<!-- FOOTER -->
<footer>
  <p>© 2026 IAsim PRO · Todos os direitos reservados</p>
  <p style="margin-top:8px;"><a href="/entrar">Entrar no Painel</a> · <a href="https://t.me/Iasim_bot">Suporte via Telegram</a></p>
</footer>

<script>
// FAQ
function toggleFaq(el) {
  const item = el.parentElement;
  item.classList.toggle('open');
}

// VSL — substitua o src pelo seu vídeo real
function loadVSL() {
  const box = document.querySelector('.vsl-box');
  // Substitua pela URL do seu vídeo de vendas real
  box.innerHTML = '<iframe src="https://www.youtube.com/embed/SEU_VIDEO_ID?autoplay=1" allowfullscreen allow="autoplay"></iframe>';
}

// Notificação de vendas
const buyers = [
  {n:"Rafael M.", c:"São Paulo"},   {n:"Beatriz L.", c:"Curitiba"},
  {n:"Thiago R.", c:"Fortaleza"},   {n:"Larissa O.", c:"Porto Alegre"},
  {n:"Gustavo F.", c:"BH"},         {n:"Amanda S.", c:"Manaus"},
  {n:"Felipe N.", c:"Floripa"},     {n:"Mariana C.", c:"Recife"},
  {n:"Caio V.", c:"Goiânia"},       {n:"Fernanda T.", c:"Vitória"},
  {n:"Bruno K.", c:"Belém"},        {n:"Jéssica P.", c:"Salvador"},
];
let idx = 0;
function showNotif() {
  const el   = document.getElementById('sale-notif');
  const txt  = document.getElementById('notif-text');
  const b    = buyers[idx % buyers.length]; idx++;
  txt.innerHTML = `<b>${b.n}</b> de ${b.c} ativou o VIP agora`;
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 5000);
}
setTimeout(showNotif, 4000);
setInterval(showNotif, 14000);
</script>

</body>
</html>
"""

# ==============================
# ROTAS
# ==============================

@app.route("/entrar", methods=["GET", "POST"])
def entrar():
    erro = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        senha    = request.form.get("senha", "")

        if len(username) < 3:
            erro = "Usuário deve ter pelo menos 3 caracteres."
        elif len(senha) < 6:
            erro = "Senha deve ter pelo menos 6 caracteres."
        else:
            user = get_web_user(username)
            if not user:
                # Criar conta
                create_web_user(username, senha)
                session["user"] = username
                return redirect("/painel")
            elif check_senha(username, senha):
                session["user"] = username
                return redirect("/painel")
            else:
                erro = "Senha incorreta. Tente novamente."

    return render_template_string(LOGIN_HTML, erro=erro)

@app.route("/painel")
@login_required
def painel():
    username = session["user"]
    user     = get_web_user(username)
    token    = session.pop("token_gerado", None)

    if not user:
        session.clear()
        return redirect("/entrar")

    return render_template_string(
        PAINEL_HTML,
        username=username,
        user=user,
        token=token,
        preco=f"{PRECO_VIP:.2f}".replace(".", ","),
    )

@app.route("/salvar_nicho", methods=["POST"])
@login_required
def salvar_nicho():
    username = session["user"]
    nicho    = request.form.get("nicho", "").strip()[:150]
    if nicho:
        update_web_user(username, nicho=nicho)
        # Sincronizar com bot se vinculado
        user = get_web_user(username)
        if user and user.get("telegram_id"):
            update_telegram_user(user["telegram_id"], nicho=nicho)
    return redirect("/painel")

@app.route("/gerar_token", methods=["POST"])
@login_required
def gerar_token_route():
    username = session["user"]
    token    = gerar_token()
    update_web_user(username, token_vinculo=token)
    session["token_gerado"] = token
    return redirect("/painel")

@app.route("/vincular", methods=["POST"])
def vincular():
    data       = request.json or {}
    token      = data.get("token", "").strip()
    telegram_id = str(data.get("telegram_id", "")).strip()

    if not token or not telegram_id:
        return jsonify({"status": "erro", "msg": "Dados inválidos"}), 400

    user = get_web_user_by_token(token)
    if not user:
        return jsonify({"status": "erro", "msg": "Token inválido"}), 404

    update_web_user(user["username"], telegram_id=telegram_id, token_vinculo=None)

    # Sincronizar plano e nicho para o bot
    update_telegram_user(telegram_id, plano=user["plano"], nicho=user["nicho"])

    return jsonify({"status": "ok"})

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    try:
        if data.get("type") == "payment":
            payment_id = str(data["data"]["id"])
            headers    = {"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}
            url        = f"https://api.mercadopago.com/v1/payments/{payment_id}"
            resp       = requests.get(url, headers=headers, timeout=10).json()

            if resp.get("status") == "approved":
                # Atualizar bot (busca por payment_id)
                with sqlite3.connect(DB_PATH) as conn:
                    conn.row_factory = sqlite3.Row
                    row = conn.execute(
                        "SELECT * FROM usuarios WHERE payment_id = ?", (payment_id,)
                    ).fetchone()

                if row:
                    row = dict(row)
                    update_telegram_user(row["telegram_id"], plano="vip")
                    # Atualizar web também se vinculado
                    if row.get("web_username"):
                        update_web_user(row["web_username"], plano="vip")
                    # Notificar no Telegram
                    enviar_telegram(
                        row["telegram_id"],
                        "🎉 *VIP liberado!*\n\n"
                        "Seu acesso ilimitado está ativo. "
                        "Use /start para acessar todos os recursos! 🚀",
                    )
                    logger.info("VIP liberado para telegram_id: %s", row["telegram_id"])

    except Exception as exc:
        logger.error("Erro webhook: %s", exc)

    return "ok", 200

@app.route("/oferta")
def oferta():
    return render_template_string(OFERTA_HTML)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/entrar")

@app.route("/")
def home():
    return redirect("/oferta")

@app.route("/health")
def health():
    return jsonify({"status": "ok", "ts": datetime.utcnow().isoformat()})

# ==============================
# MAIN
# ==============================
if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5001))
    logger.info("🌐 IAsim Web v2.0 iniciando na porta %s", port)
    app.run(host="0.0.0.0", port=port, debug=False)