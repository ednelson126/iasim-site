from flask import Flask, request, render_template_string, session, redirect
import json
import requests
import os

app = Flask(__name__)
app.secret_key = "iasim_secret_key_2026"

# ==============================
# CONFIG
# ==============================
MP_ACCESS_TOKEN = "APP_USR-7479127174794036-041215-232df09bcca56ad0d165a4fb4b6708c0-367052923"
TELEGRAM_TOKEN = "8764613490:AAEtMUmgS0JhL3EsYze10HnWX52juMlIMCQ"

ARQUIVO = "usuarios.json"

# ==============================
# BANCO
# ==============================
def carregar():
    try:
        with open(ARQUIVO, "r") as f:
            return json.load(f)
    except:
        return {}

def salvar(dados):
    with open(ARQUIVO, "w") as f:
        json.dump(dados, f, indent=4)

# ==============================
# TELEGRAM
# ==============================
def enviar_telegram(user_id, msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": user_id, "text": msg})
    except:
        pass

# ==============================
# LOGIN
# ==============================
@app.route('/login')
def login():
    user_id = request.args.get("user_id")

    usuarios = carregar()

    if user_id not in usuarios:
        usuarios[user_id] = {"plano": "gratis", "uso": 0}
        salvar(usuarios)

    session["user_id"] = user_id
    return redirect("/painel")

# ==============================
# PAINEL CLIENTE
# ==============================
@app.route('/painel')
def painel():
    user_id = session.get("user_id")

    if not user_id:
        return "Acesse via /login?user_id=SEU_ID"

    usuarios = carregar()
    user = usuarios.get(user_id)

    html = f"""
    <html>
    <head>
        <title>IAsim PRO</title>
        <style>
            body {{
                background: #0f172a;
                color: white;
                font-family: Arial;
                text-align: center;
                padding: 40px;
            }}
            .box {{
                background: #1e293b;
                padding: 30px;
                border-radius: 10px;
                display: inline-block;
                box-shadow: 0 0 20px rgba(0,0,0,0.5);
            }}
            .vip {{
                color: #22c55e;
                font-weight: bold;
            }}
            button {{
                padding: 10px 20px;
                margin: 10px;
                border: none;
                border-radius: 5px;
                background: #22c55e;
                color: white;
                cursor: pointer;
            }}
            input {{
                padding: 10px;
                border-radius: 5px;
                border: none;
                width: 80%;
            }}
        </style>
    </head>
    <body>

        <div class="box">
            <h1>🤖 IAsim PRO</h1>

            <p>ID: {user_id}</p>
            <p>Plano: <span class="vip">{user.get("plano")}</span></p>
            <p>Nicho: {user.get("nicho", "Não definido")}</p>

            <form action="/salvar_nicho">
                <input type="hidden" name="user_id" value="{user_id}">
                <input type="text" name="nicho" placeholder="Digite seu nicho">
                <br>
                <button type="submit">Salvar Nicho</button>
            </form>

            <br><br>

            <a href="https://t.me/seubot">
                <button>🚀 Acessar Bot</button>
            </a>

        </div>

    </body>
    </html>
    """

    return render_template_string(html)

# ==============================
# ADMIN
# ==============================
@app.route('/admin')
def admin():
    usuarios = carregar()

    lista = ""

    for uid, dados in usuarios.items():
        lista += f"<p>{uid} - {dados.get('plano')}</p>"

    return f"""
    <h1>Painel Admin</h1>
    {lista}
    """

# ==============================
# SALVAR NICHO
# ==============================
@app.route('/salvar_nicho')
def salvar_nicho():
    user_id = request.args.get("user_id")
    nicho = request.args.get("nicho")

    usuarios = carregar()

    if user_id in usuarios:
        usuarios[user_id]["nicho"] = nicho
        salvar(usuarios)

    return redirect("/painel")

# ==============================
# WEBHOOK (AUTO VIP)
# ==============================
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json

    try:
        if data.get("type") == "payment":
            payment_id = data["data"]["id"]

            headers = {"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}
            url = f"https://api.mercadopago.com/v1/payments/{payment_id}"

            resp = requests.get(url, headers=headers).json()

            if resp.get("status") == "approved":
                usuarios = carregar()

                for user_id, dados in usuarios.items():
                    if dados.get("payment_id") == payment_id:
                        usuarios[user_id]["plano"] = "vip"
                        salvar(usuarios)

                        enviar_telegram(user_id, "🎉 VIP liberado automaticamente!")

    except Exception as e:
        print("Erro webhook:", e)

    return "ok"

# ==============================
# HOME
# ==============================
@app.route('/')
def home():
    return "IAsim SaaS PRO Online 🚀"

# ==============================
# MAIN
# ==============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)