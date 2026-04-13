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
TELEGRAM_TOKEN = "8764613490:AAEtMUmgM0JhL3EsYze10HnWX52juMlIMCQ"

ARQUIVO = "usuarios.json"


# ==============================
# BANCO DE DADOS (JSON)
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
# TELEGRAM NOTIFICAÇÃO
# ==============================
def enviar_telegram(user_id, msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": user_id, "text": msg})
    except:
        pass


# ==============================
# HOME
# ==============================
@app.route("/")
def home():
    return """
    <h2>IAsim SaaS Online 🚀</h2>
    <p>Use /login?user_id=SEU_ID para acessar</p>
    """


# ==============================
# LOGIN (SaaS REAL)
# ==============================
@app.route("/login")
def login():
    user_id = request.args.get("user_id")

    usuarios = carregar()

    if user_id in usuarios:
        session["user_id"] = user_id
        return """
        <h3>Login realizado com sucesso 🚀</h3>
        <a href="/painel">Ir para o painel</a>
        """

    # cria usuário automaticamente (SaaS real)
    usuarios[user_id] = {
        "plano": "gratis",
        "uso": 0,
        "payment_id": None,
        "nicho": ""
    }

    salvar(usuarios)
    session["user_id"] = user_id

    return redirect("/painel")


# ==============================
# LOGOUT
# ==============================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ==============================
# PAINEL SAAS PROFISSIONAL
# ==============================
@app.route("/painel")
def painel():

    user_id = session.get("user_id")

    if not user_id:
        return redirect("/")

    usuarios = carregar()
    user = usuarios.get(user_id)

    if not user:
        return "Usuário não encontrado"

    vip = user["plano"] == "vip"

    return render_template_string(f"""
    <html>
    <head>
        <title>IAsim SaaS</title>
        <style>
            body {{
                font-family: Arial;
                background: #0f172a;
                color: white;
                text-align: center;
                padding: 40px;
            }}
            .box {{
                background: #1e293b;
                padding: 30px;
                border-radius: 12px;
                display: inline-block;
                width: 400px;
            }}
            button {{
                padding: 10px;
                margin: 5px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                width: 90%;
            }}
            .vip {{
                background: green;
                color: white;
            }}
            .free {{
                background: red;
                color: white;
            }}
        </style>
    </head>

    <body>

        <div class="box">
            <h2>🤖 IAsim SaaS</h2>

            <p><b>Plano:</b> {user["plano"]}</p>
            <p><b>Nicho:</b> {user.get("nicho", "")}</p>

            <hr>

            <form action="/salvar_nicho">
                <input type="hidden" name="user_id" value="{user_id}">
                <input type="text" name="nicho" placeholder="Seu nicho">
                <br><br>
                <button>Salvar Nicho</button>
            </form>

            <br>

            {"<button class='vip'>✔ VIP ATIVO</button>" if vip else "<a href='/vip'><button class='free'>💰 ATIVAR VIP</button></a>"}

            <br><br>

            <a href="/logout">
                <button style="background:#333;color:white;">Sair</button>
            </a>

        </div>

    </body>
    </html>
    """)


# ==============================
# SALVAR NICHO
# ==============================
@app.route("/salvar_nicho")
def salvar_nicho():
    user_id = request.args.get("user_id")
    nicho = request.args.get("nicho")

    usuarios = carregar()

    if user_id in usuarios:
        usuarios[user_id]["nicho"] = nicho
        salvar(usuarios)

    return redirect("/painel")


# ==============================
# VIP (MERCADO PAGO PIX)
# ==============================
@app.route("/vip")
def vip():
    return """
    <h2>Plano VIP IAsim</h2>
    <p>Valor: R$19,90</p>

    <p>Após pagamento, o acesso será liberado automaticamente.</p>

    <p>🔗 Pagamento integrado via Mercado Pago Webhook</p>
    """


# ==============================
# WEBHOOK MERCADO PAGO
# ==============================
@app.route("/webhook", methods=["POST"])
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

                        enviar_telegram(
                            user_id,
                            "🎉 VIP liberado automaticamente!"
                        )

    except Exception as e:
        print("Webhook erro:", e)

    return "ok"


# ==============================
# MAIN (RENDER)
# ==============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)