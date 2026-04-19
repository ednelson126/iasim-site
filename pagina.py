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
                max-width: 850px;
                margin: auto;
                padding: 20px;
            }

            .box {
                background: #1e293b;
                padding: 25px;
                border-radius: 10px;
                margin-top: 20px;
                box-shadow: 0 0 20px rgba(0,0,0,0.6);
                text-align: left;
            }

            h1, h2, h3 {
                text-align: center;
            }

            h1 { color: #22c55e; }

            button {
                padding: 15px;
                background: #22c55e;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 18px;
                cursor: pointer;
                width: 100%;
                margin-top: 15px;
                font-weight: bold;
            }

            .price {
                font-size: 36px;
                color: #22c55e;
                text-align: center;
                margin: 10px;
            }

            .highlight {
                color: #22c55e;
                font-weight: bold;
            }

            iframe {
                width: 100%;
                height: 400px;
                border-radius: 10px;
            }

            .timer {
                font-size: 22px;
                color: #facc15;
                text-align: center;
                font-weight: bold;
            }
        </style>

        <script>
            function startTimer() {
                var time = 1200;

                setInterval(function() {
                    var min = Math.floor(time / 60);
                    var sec = time % 60;

                    document.getElementById("timer").innerHTML =
                        "⏳ Essa página pode sair do ar em: " + min + ":" + (sec < 10 ? "0" : "") + sec;

                    if (time > 0) time--;
                }, 1000);
            }

            window.onload = startTimer;
        </script>

    </head>

    <body>

        <div class="container">

            <h1>🤖 IAsim PRO</h1>
            <h2>O jeito mais simples de começar a ganhar dinheiro com IA ainda hoje</h2>

            <!-- VSL -->
            <div class="box">
                <h3>⚠️ Assista isso antes de tomar qualquer decisão</h3>
                <iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ"></iframe>
            </div>

            <!-- DOR -->
            <div class="box">
                <h3>Seja sincero...</h3>

                <p>Você já tentou ganhar dinheiro na internet e não conseguiu?</p>

                <p>Já viu pessoas crescendo enquanto você continua no mesmo lugar?</p>

                <p class="highlight">E isso começa a dar uma sensação ruim… de estar ficando pra trás.</p>
            </div>

            <!-- HISTÓRIA -->
            <div class="box">
                <h3>A diferença entre quem consegue e quem não consegue</h3>

                <p>Não é inteligência.</p>
                <p>Não é sorte.</p>

                <p class="highlight">É acesso às ferramentas certas.</p>

                <p>E hoje, quem usa IA está anos na frente.</p>
            </div>

            <!-- SOLUÇÃO -->
            <div class="box">
                <h3>🚀 Foi por isso que criamos o IAsim PRO</h3>

                <p>Um sistema que literalmente pensa por você.</p>

                <p class="highlight">Ele cria conteúdo, ideias e estratégias automaticamente.</p>
            </div>

            <!-- DETALHAMENTO EXTREMO -->
            <div class="box">
                <h3>💡 Tudo que você recebe:</h3>

                <p><b>🔥 Ideias virais:</b><br>
                Nunca mais fique travado. Receba ideias que prendem atenção imediatamente.</p>

                <p><b>🎬 Roteiros prontos:</b><br>
                Vídeos estruturados para engajar e crescer.</p>

                <p><b>📱 Conteúdos completos:</b><br>
                Textos prontos para copiar e usar.</p>

                <p><b>💰 Estratégias de venda:</b><br>
                Técnicas usadas por quem realmente ganha dinheiro.</p>

                <p class="highlight">
                Tudo isso direto no Telegram, simples e rápido.
                </p>
            </div>

            <!-- PROVA -->
            <div class="box">
                <h3>💬 Resultados reais</h3>

                <p>⭐⭐⭐⭐⭐ “Nunca mais fiquei sem ideia”</p>
                <p>⭐⭐⭐⭐⭐ “Comecei do zero e já estou postando todo dia”</p>
                <p>⭐⭐⭐⭐⭐ “Simples e poderoso”</p>
            </div>

            <!-- QUEBRA DE OBJEÇÃO -->
            <div class="box">
                <h3>❌ Não é pra você se:</h3>

                <p>Você não quer agir.</p>
                <p>Prefere continuar tentando sozinho.</p>

                <h3>✅ É pra você se:</h3>

                <p>Quer algo pronto.</p>
                <p>Quer começar rápido.</p>
                <p>Quer resultado.</p>
            </div>

            <!-- URGÊNCIA -->
            <div class="box">
                <p id="timer" class="timer"></p>
                <p style="text-align:center;">⚠️ Essa condição pode sair do ar a qualquer momento</p>
            </div>

            <!-- ANCORAGEM -->
            <div class="box">
                <h3>💰 Quanto isso deveria custar?</h3>

                <p>Se fosse um curso completo… seria facilmente R$197 ou mais.</p>

                <p>Mas hoje você não vai pagar isso.</p>
            </div>

            <!-- OFERTA -->
            <div class="box">
                <h3>🔥 Oferta especial hoje</h3>

                <p class="price">R$19,90</p>

                <p style="text-align:center;">
                Pagamento único • Acesso imediato
                </p>

                <a href="https://t.me/Iasim_bot">
                    <button>🚀 QUERO ACESSAR AGORA</button>
                </a>
            </div>

            <!-- GARANTIA -->
            <div class="box">
                <h3>🔒 Zero risco</h3>

                <p>Você pode testar e ver por conta própria.</p>

                <p class="highlight">Sem risco. Sem complicação.</p>
            </div>

            <!-- FECHAMENTO -->
            <div class="box">
                <h3>Agora a escolha é sua</h3>

                <p>Continuar parado…</p>

                <p>Ou começar agora com algo pronto.</p>

                <p class="highlight">A oportunidade está aqui.</p>

                <a href="https://t.me/Iasim_bot">
                    <button>🔥 COMEÇAR AGORA</button>
                </a>
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