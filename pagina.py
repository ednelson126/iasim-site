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
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": user_id, "text": msg})
    except:
        print("Erro Telegram")

# ==============================
# LANDING PAGE
# ==============================
@app.route('/oferta')
def oferta():
    return """
    <html>
    <head>
        <title>IAsim PRO</title>

        <style>
            body {
                margin: 0;
                font-family: Arial;
                background: linear-gradient(135deg, #020617, #0f172a);
                color: white;
                text-align: center;
            }

            .container {
                max-width: 700px;
                margin: auto;
                padding: 40px 20px;
            }

            h1 {
                font-size: 32px;
                margin-bottom: 20px;
            }

            h2 {
                color: #22c55e;
            }

            p {
                font-size: 18px;
                line-height: 1.6;
            }

            .box {
                background: #1e293b;
                padding: 25px;
                border-radius: 12px;
                margin: 20px 0;
                box-shadow: 0 0 20px rgba(0,0,0,0.5);
            }

            .btn {
                background: #22c55e;
                color: white;
                padding: 15px 30px;
                border: none;
                border-radius: 8px;
                font-size: 18px;
                cursor: pointer;
                margin-top: 20px;
                display: inline-block;
                text-decoration: none;
                font-weight: bold;
            }

            .btn:hover {
                background: #16a34a;
            }

            .alert {
                color: #facc15;
                font-weight: bold;
                margin-top: 20px;
            }

            .price {
                font-size: 28px;
                color: #22c55e;
                font-weight: bold;
            }

        </style>
    </head>

    <body>

        <div class="container">

            <h1>💰 Ganhe dinheiro com Inteligência Artificial todos os dias</h1>

            <p>
                Mesmo começando do zero, sem experiência e sem aparecer.
            </p>

            <a href="https://t.me/Iasim_bot" class="btn">
                🚀 COMEÇAR AGORA
            </a>

            <div class="box">
                <h2>🤖 O que você recebe:</h2>

                <p>✔ Ideias virais prontas para postar</p>
                <p>✔ Roteiros curtos que prendem atenção</p>
                <p>✔ Conteúdos que geram engajamento</p>
                <p>✔ Estratégias para vender todos os dias</p>
                <p>✔ Sistema automatizado com IA</p>
            </div>

            <div class="box">
                <h2>🔥 Para quem é:</h2>

                <p>✔ Quem quer ganhar dinheiro online</p>
                <p>✔ Criadores de conteúdo</p>
                <p>✔ Afiliados e iniciantes</p>
                <p>✔ Pessoas que querem renda extra</p>
            </div>

            <div class="box">
                <h2>🚫 Para quem NÃO é:</h2>

                <p>❌ Quem quer resultados sem fazer nada</p>
                <p>❌ Quem não vai aplicar o conteúdo</p>
            </div>

            <div class="box">
                <h2>💵 Investimento</h2>

                <p class="price">R$19,90</p>

                <p>Acesso completo ao sistema</p>

                <a href="https://t.me/Iasim_bot" class="btn">
                    🔥 QUERO ACESSAR AGORA
                </a>
            </div>

            <p class="alert">
                ⚠️ Acesso pode sair do ar a qualquer momento
            </p>

            <p style="margin-top:40px; font-size:14px;">
                © IAsim PRO - Todos os direitos reservados
            </p>

        </div>

    </body>
    </html>
    """

# ==============================
# LOGIN ANTIGO (COMPATIBILIDADE)
# ==============================
@app.route('/login')
def login_antigo():
    user_id = request.args.get("user_id")

    if user_id:
        session["user_id"] = user_id
        return redirect("/painel")

    return redirect("/entrar")

# ==============================
# LOGIN FORMULÁRIO
# ==============================
@app.route('/entrar', methods=['GET', 'POST'])
def entrar():
    if request.method == 'POST':
        user_id = request.form.get("user_id")
        senha = request.form.get("senha")

        usuarios = carregar()

        if user_id not in usuarios:
            # cria novo usuário
            usuarios[user_id] = {
                "plano": "gratis",
                "senha": senha
            }
            salvar(usuarios)
        else:
            # verifica senha
            if usuarios[user_id].get("senha") != senha:
                return "❌ Senha incorreta"

        session["user_id"] = user_id
        return redirect("/painel")

    return """
    <html>
    <body style="text-align:center; padding:50px;">
        <h2>Login IAsim</h2>
        <form method="POST">
            <input name="user_id" placeholder="Seu ID"><br><br>
            <input name="senha" type="password" placeholder="Sua senha"><br><br>
            <button type="submit">Entrar</button>
        </form>
    </body>
    </html>
    """

# ==============================
# PAINEL PROFISSIONAL
# ==============================
@app.route('/painel')
def painel():
    user_id = session.get("user_id")

    if not user_id:
        return redirect("/entrar")

    usuarios = carregar()
    user = usuarios.get(user_id)

    if not user:
        return "Usuário não encontrado"

    html = f"""
    <html>
    <head>
        <title>IAsim PRO</title>
        <style>
            body {{
                background: linear-gradient(135deg, #0f172a, #020617);
                color: white;
                font-family: Arial;
                text-align: center;
                padding: 40px;
            }}

            .box {{
                background: #1e293b;
                padding: 40px;
                border-radius: 15px;
                display: inline-block;
                box-shadow: 0 0 25px rgba(0,0,0,0.7);
                width: 320px;
            }}

            .plano {{
                color: #22c55e;
                font-weight: bold;
                font-size: 18px;
            }}

            input {{
                padding: 12px;
                border-radius: 8px;
                border: none;
                width: 90%;
                margin-top: 10px;
            }}

            button {{
                background: #22c55e;
                color: white;
                padding: 12px;
                border: none;
                border-radius: 8px;
                margin-top: 10px;
                cursor: pointer;
                width: 90%;
                font-weight: bold;
            }}

            .logout {{
                background: #ef4444;
            }}
        </style>
    </head>

    <body>
        <div class="box">
            <h1>🚀 IAsim PRO</h1>

            <p>Plano:</p>
            <p class="plano">{user.get("plano")}</p>

            <p>Nicho:</p>
            <p>{user.get("nicho", "Não definido")}</p>

            <form action="/salvar_nicho">
                <input type="hidden" name="user_id" value="{user_id}">
                <input name="nicho" placeholder="Digite seu nicho">
                <button type="submit">Salvar Nicho</button>
            </form>

            <a href="https://t.me/Iasim_bot">
                <button>🤖 Acessar Bot</button>
            </a>

            <a href="/logout">
                <button class="logout">Sair</button>
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

    return redirect("/painel")

# ==============================
# LOGOUT
# ==============================
@app.route('/logout')
def logout():
    session.clear()
    return redirect("/entrar")

# ==============================
# ADMIN
# ==============================
@app.route('/admin')
def admin():
    usuarios = carregar()

    total = len(usuarios)
    vip = sum(1 for u in usuarios.values() if u.get("plano") == "vip")

    lista = "".join([f"<p>{uid} - {u.get('plano')}</p>" for uid, u in usuarios.items()])

    return f"""
    <h1>📊 Painel Admin</h1>
    <p>Total usuários: {total}</p>
    <p>VIPs: {vip}</p>
    <hr>
    {lista}
    """

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