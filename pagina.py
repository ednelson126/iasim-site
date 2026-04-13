from flask import Flask, request, render_template_string
import json
import requests

app = Flask(__name__)

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
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": user_id, "text": msg})
    except:
        print("Erro ao enviar mensagem Telegram")

# ==============================
# WEBHOOK (MERCADO PAGO)
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

                        enviar_telegram(
                            user_id,
                            "🎉 Pagamento aprovado! VIP liberado 🚀"
                        )
    except Exception as e:
        print("Erro webhook:", e)

    return "ok"

# ==============================
# PAINEL CLIENTE
# ==============================
@app.route('/painel')
def painel():
    user_id = request.args.get("user_id")

    usuarios = carregar()
    user = usuarios.get(user_id)

    if not user:
        return "Usuário não encontrado"

    html = f"""
    <html>
    <head>
        <title>IAsim Painel</title>
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
                border-radius: 10px;
                display: inline-block;
                box-shadow: 0 0 20px rgba(0,0,0,0.5);
            }}
            button {{
                padding: 10px 20px;
                margin: 10px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                background: #22c55e;
                color: white;
                font-weight: bold;
            }}
            input {{
                padding: 10px;
                border-radius: 5px;
                border: none;
                margin-top: 10px;
                width: 80%;
            }}
        </style>
    </head>
    <body>

        <div class="box">
            <h1>🤖 IAsim Dashboard</h1>

            <p><b>Plano:</b> {user.get("plano")}</p>
            <p><b>Nicho:</b> {user.get("nicho", "Não definido")}</p>

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

    return f"Nicho salvo: {nicho}"

# ==============================
# HOME
# ==============================
@app.route('/')
def home():
    return "IAsim online 🚀"

# ==============================
# MAIN
# ==============================
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)