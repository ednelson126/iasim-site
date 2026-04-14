from flask import Flask, request, render_template_string, session, redirect
import json
import requests
import os
import random
import string

app = Flask(__name__)
app.secret_key = "iasim_secret_key_2026"

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
# GERAR TOKEN
# ==============================
def gerar_token():
    return "IASIM-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

# ==============================
# TELEGRAM
# ==============================
def enviar_telegram(user_id, msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": user_id, "text": msg})
    except:
        print("Erro Telegram")

# ==============================
# LOGIN
# ==============================
@app.route('/entrar', methods=['GET', 'POST'])
def entrar():
    if request.method == 'POST':
        username = request.form.get("username")
        senha = request.form.get("senha")

        usuarios = carregar()

        if username not in usuarios:
            usuarios[username] = {
                "senha": senha,
                "plano": "gratis",
                "telegram_id": None,
                "token": None
            }
            salvar(usuarios)
        else:
            if usuarios[username]["senha"] != senha:
                return "❌ Senha incorreta"

        session["user"] = username
        return redirect("/painel")

    return """
    <h2 style='text-align:center'>Login IAsim</h2>
    <form method="POST" style='text-align:center'>
        <input name="username" placeholder="Usuário"><br><br>
        <input name="senha" type="password" placeholder="Senha"><br><br>
        <button type="submit">Entrar / Criar Conta</button>
    </form>
    """

# ==============================
# PAINEL
# ==============================
@app.route('/painel')
def painel():
    username = session.get("user")

    if not username:
        return redirect("/entrar")

    usuarios = carregar()
    user = usuarios.get(username)

    if not user:
        return "Usuário não encontrado"

    html = f"""
    <html>
    <head>
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
            }}
        </style>
    </head>
    <body>

        <div class="box">
            <h1>🚀 IAsim PRO</h1>

            <p><b>Plano:</b> {user.get("plano")}</p>
            <p><b>Nicho:</b> {user.get("nicho","Não definido")}</p>

            <form action="/salvar_nicho">
                <input type="hidden" name="username" value="{username}">
                <input name="nicho" placeholder="Seu nicho">
                <br>
                <button>Salvar Nicho</button>
            </form>

            <hr>

            <p><b>Telegram:</b> {user.get("telegram_id") or "Não conectado"}</p>

            <a href="/gerar_token">
                <button>🔗 Conectar Telegram</button>
            </a>

            <br>

            <a href="https://t.me/Iasim_bot">
                <button>🤖 Abrir Bot</button>
            </a>

            <br>

            <a href="/logout">
                <button style="background:red;">Sair</button>
            </a>
        </div>

    </body>
    </html>
    """

    return render_template_string(html)

# ==============================
# GERAR TOKEN
# ==============================
@app.route('/gerar_token')
def gerar_token_route():
    username = session.get("user")
    usuarios = carregar()

    token = gerar_token()
    usuarios[username]["token"] = token
    salvar(usuarios)

    return f"""
    <h2>🔐 Código gerado</h2>
    <p>{token}</p>
    <p>Envie no bot:</p>
    <b>/vincular {token}</b>
    """

# ==============================
# SALVAR NICHO
# ==============================
@app.route('/salvar_nicho')
def salvar_nicho():
    username = request.args.get("username")
    nicho = request.args.get("nicho")

    usuarios = carregar()

    if username in usuarios:
        usuarios[username]["nicho"] = nicho
        salvar(usuarios)

    return redirect("/painel")

# ==============================
# VINCULAR
# ==============================
@app.route('/vincular', methods=['POST'])
def vincular():
    data = request.json
    token = data.get("token")
    telegram_id = data.get("telegram_id")

    usuarios = carregar()

    for user, dados in usuarios.items():
        if dados.get("token") == token:
            usuarios[user]["telegram_id"] = telegram_id
            usuarios[user]["token"] = None
            salvar(usuarios)
            return {"status": "ok"}

    return {"status": "erro"}

# ==============================
# WEBHOOK
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

                for user, dados in usuarios.items():
                    if dados.get("payment_id") == payment_id:
                        usuarios[user]["plano"] = "vip"
                        salvar(usuarios)

                        if dados.get("telegram_id"):
                            enviar_telegram(
                                dados["telegram_id"],
                                "🎉 VIP liberado!"
                            )
    except Exception as e:
        print(e)

    return "ok"

# ==============================
# PÁGINA DE VENDAS
# ==============================
@app.route('/oferta')
def oferta():
    return """
    <html>
    <head>
        <title>IAsim PRO</title>

        <style>
            body {
                font-family: Arial;
                background: #0f172a;
                color: white;
                margin: 0;
                text-align: center;
            }

            .container {
                max-width: 800px;
                margin: auto;
                padding: 20px;
            }

            .box {
                background: #1e293b;
                padding: 25px;
                border-radius: 10px;
                margin-top: 20px;
                box-shadow: 0 0 20px rgba(0,0,0,0.5);
            }

            h1 { color: #22c55e; }

            button {
                padding: 15px 25px;
                background: #22c55e;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 18px;
                cursor: pointer;
                margin-top: 20px;
                font-weight: bold;
            }

            .price {
                font-size: 32px;
                margin: 20px;
                color: #22c55e;
            }

            .timer {
                font-size: 22px;
                color: #facc15;
                font-weight: bold;
            }

            iframe {
                width: 100%;
                height: 400px;
                border-radius: 10px;
            }
        </style>

        <script>
            function startTimer() {
                var time = 600; // 10 minutos

                setInterval(function() {
                    var min = Math.floor(time / 60);
                    var sec = time % 60;

                    document.getElementById("timer").innerHTML =
                        "⏳ Oferta expira em: " + min + ":" + (sec < 10 ? "0" : "") + sec;

                    if (time > 0) {
                        time--;
                    }
                }, 1000);
            }

            window.onload = startTimer;
        </script>
    </head>

    <body>

        <div class="container">

            <h1>🤖 IAsim PRO</h1>
            <h2>Ganhe dinheiro com IA automaticamente</h2>

            <!-- VSL -->
            <div class="box">
                <h3>🎥 Assista antes de começar</h3>
                <iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ"
                allowfullscreen></iframe>
            </div>

            <!-- COPY -->
            <div class="box">
                <p>Você está vendo pessoas ganhando dinheiro com Inteligência Artificial...</p>
                <p><b>Mas não sabe por onde começar?</b></p>

                <p style="color:#22c55e;">
                Esse sistema faz isso por você automaticamente.
                </p>
            </div>

            <!-- BENEFÍCIOS -->
            <div class="box">
                <h3>🚀 O que você recebe:</h3>
                <p>✔ Ideias virais prontas</p>
                <p>✔ Roteiros para vídeos</p>
                <p>✔ Conteúdos prontos</p>
                <p>✔ Estratégias de vendas</p>
                <p>✔ Bot exclusivo no Telegram</p>
            </div>

            <!-- PROVA SOCIAL -->
            <div class="box">
                <h3>💬 Depoimentos</h3>

                <p>⭐⭐⭐⭐⭐ “Comecei ontem e já tive ideias incríveis!”</p>
                <p>⭐⭐⭐⭐⭐ “Muito melhor do que eu esperava!”</p>
                <p>⭐⭐⭐⭐⭐ “Simplesmente funciona!”</p>
                <p>⭐⭐⭐⭐⭐ “Já estou aplicando e vendo resultado!”</p>
            </div>

            <!-- CONTADOR -->
            <div class="box">
                <p id="timer" class="timer"></p>
                <p>⚠️ A oferta pode encerrar a qualquer momento</p>
            </div>

            <!-- PREÇO -->
            <div class="box">
                <h3>💰 Oferta Especial</h3>

                <div class="price">R$19,90</div>

                <a href="https://t.me/Iasim_bot">
                    <button>🚀 COMEÇAR AGORA</button>
                </a>

                <p>Pagamento único • Acesso imediato</p>
            </div>

            <!-- GARANTIA -->
            <div class="box">
                <h3>🔒 Garantia</h3>
                <p>Teste sem risco. Acesso imediato ao sistema.</p>
            </div>

        </div>

    </body>
    </html>
    """

# ==============================
# LOGOUT
# ==============================
@app.route('/logout')
def logout():
    session.clear()
    return redirect("/entrar")

# ==============================
# HOME
# ==============================
@app.route('/')
def home():
    return "IAsim SaaS Online 🚀"

# ==============================
# MAIN
# ==============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)