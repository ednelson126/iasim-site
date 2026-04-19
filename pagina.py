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
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>IAsim PRO - Dominando a Inteligência Artificial</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700;900&display=swap" rel="stylesheet">
        
        <style>
            :root {
                --primary: #00ff88;
                --primary-hover: #00cc6d;
                --bg: #05070a;
                --card: #111827;
                --accent: #3b82f6;
            }

            body {
                font-family: 'Montserrat', sans-serif;
                background: var(--bg);
                color: #e5e7eb;
                margin: 0;
                overflow-x: hidden;
            }

            /* Notificação de Venda Fake (Gatilho de Prova Social) */
            #sale-notification {
                position: fixed;
                bottom: 20px;
                left: 20px;
                background: white;
                color: #333;
                padding: 12px 20px;
                border-radius: 50px;
                display: flex;
                align-items: center;
                gap: 12px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.5);
                z-index: 1000;
                transform: translateY(150%);
                transition: transform 0.5s ease;
                font-size: 13px;
            }

            /* Headline de Alto Impacto */
            .hero {
                padding: 60px 20px;
                background: radial-gradient(circle at top, #1e293b 0%, #05070a 100%);
                text-align: center;
            }

            .badge {
                background: rgba(0, 255, 136, 0.1);
                color: var(--primary);
                padding: 6px 15px;
                border-radius: 20px;
                font-weight: bold;
                font-size: 12px;
                text-transform: uppercase;
                margin-bottom: 20px;
                display: inline-block;
            }

            h1 {
                font-weight: 900;
                font-size: 2.8rem;
                letter-spacing: -1px;
                margin: 10px 0;
                line-height: 1.1;
            }

            .highlight { color: var(--primary); }

            /* Grid de Benefícios Ultra */
            .features-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin: 40px 0;
            }

            .feature-card {
                background: var(--card);
                padding: 25px;
                border-radius: 20px;
                border: 1px solid #1f2937;
                transition: 0.3s;
            }

            .feature-card i {
                font-size: 30px;
                color: var(--primary);
                margin-bottom: 15px;
            }

            /* Mockup de Checkout (Aumenta Confiança) */
            .checkout-preview {
                background: #f8fafc;
                color: #1e293b;
                border-radius: 15px;
                padding: 20px;
                margin-top: 30px;
                text-align: left;
            }

            .payment-methods {
                display: flex;
                gap: 10px;
                margin-top: 15px;
                filter: grayscale(1);
                opacity: 0.6;
            }

            /* Botão de Compra - Efeito Glossy */
            .btn-glow {
                background: linear-gradient(135deg, #00ff88 0%, #00bd65 100%);
                color: #000 !important;
                font-weight: 900;
                padding: 25px;
                border-radius: 15px;
                display: block;
                text-decoration: none;
                font-size: 1.4rem;
                text-align: center;
                box-shadow: 0 0 20px rgba(0, 255, 136, 0.3);
                position: relative;
                overflow: hidden;
            }

            .btn-glow::after {
                content: '';
                position: absolute;
                top: -50%;
                left: -50%;
                width: 200%;
                height: 200%;
                background: rgba(255,255,255,0.2);
                transform: rotate(45deg);
                transition: 0.5s;
                animation: flare 3s infinite;
            }

            @keyframes flare {
                0% { left: -150%; }
                100% { left: 150%; }
            }

            /* Estilo Depoimentos Stories */
            .stories-scroll {
                display: flex;
                overflow-x: auto;
                gap: 15px;
                padding: 20px 0;
                scrollbar-width: none;
            }

            .story-card {
                min-width: 150px;
                height: 250px;
                background: #333;
                border-radius: 15px;
                position: relative;
                background-size: cover;
                background-position: center;
                border: 2px solid var(--primary);
            }

            @media (max-width: 600px) {
                h1 { font-size: 2rem; }
            }
        </style>
    </head>
    <body>

    <div id="sale-notification">
        <i class="fas fa-shopping-cart" style="color: var(--primary)"></i>
        <span id="notification-text">Marcos de Belém acabou de adquirir o PRO</span>
    </div>

    <div class="hero">
        <div class="badge">Acesso Vitalício Liberado</div>
        <h1>DEIXE A <span class="highlight">IA TRABALHAR</span> ENQUANTO VOCÊ LUCRA.</h1>
        <p style="font-size: 18px; color: #94a3b8;">A ferramenta definitiva para quem quer escalar negócios digitais em 2026.</p>
    </div>

    <div class="container" style="max-width: 900px; margin: auto; padding: 0 20px;">
        
        <div style="box-shadow: 0 0 50px rgba(0, 255, 136, 0.2); border-radius: 20px; overflow: hidden; margin-bottom: 50px;">
             <div style="padding-bottom:56.25%; position:relative;">
                <iframe style="position:absolute; top:0; left:0; width:100%; height:100%;" src="https://www.youtube.com/embed/dQw4w9WgXcQ" frameborder="0" allow="autoplay; encrypted-media" allowfullscreen></iframe>
             </div>
        </div>

        <div class="features-grid">
            <div class="feature-card">
                <i class="fas fa-brain"></i>
                <h3>Cérebro Digital</h3>
                <p>Nossa IA aprende seu tom de voz e cria roteiros que conectam emocionalmente.</p>
            </div>
            <div class="feature-card">
                <i class="fas fa-bolt"></i>
                <h3>Velocidade</h3>
                <p>O que levava 5 horas para produzir agora leva 30 segundos cronometrados.</p>
            </div>
            <div class="feature-card">
                <i class="fas fa-chart-line"></i>
                <h3>Escala Real</h3>
                <p>Crie 30 dias de conteúdo em uma tarde e domine todos os canais de venda.</p>
            </div>
        </div>

        <h2 style="text-align: center;">Resultados Reais de Alunos</h2>
        <div class="stories-scroll">
            <div class="story-card" style="background-image: url('https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?auto=format&fit=crop&w=300&q=80')"></div>
            <div class="story-card" style="background-image: url('https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&w=300&q=80')"></div>
            <div class="story-card" style="background-image: url('https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=300&q=80')"></div>
            <div class="story-card" style="background-image: url('https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=300&q=80')"></div>
        </div>

        <div class="feature-card" style="margin-top: 50px; border: 2px solid var(--primary);">
            <div style="text-align: center;">
                <h2 style="margin: 0;">OFERTA DE LANÇAMENTO</h2>
                <p style="text-decoration: line-through; opacity: 0.5;">De R$ 297,00</p>
                <h1 style="font-size: 4rem; margin: 10px 0;" class="highlight">R$ 19,90</h1>
                <p>Ou 2x de R$ 10,38 no cartão</p>
            </div>

            <div class="checkout-preview">
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #ddd; padding-bottom: 10px;">
                    <span><b>IAsim PRO - Licença Premium</b></span>
                    <span style="color: #16a34a;">R$ 19,90</span>
                </div>
                <p style="font-size: 12px; margin-top: 10px;"><i class="fas fa-lock"></i> Pagamento processado em ambiente 100% seguro.</p>
                <div class="payment-methods">
                    <i class="fab fa-cc-visa fa-2x"></i>
                    <i class="fab fa-cc-mastercard fa-2x"></i>
                    <i class="fas fa-qrcode fa-2x"></i>
                </div>
            </div>

            <a href="https://t.me/Iasim_bot" class="btn-glow" style="margin-top: 20px;">
                QUERO MEU ACESSO AGORA <i class="fas fa-arrow-right"></i>
            </a>
            
            <p style="text-align: center; font-size: 12px; margin-top: 15px; opacity: 0.7;">
                Vagas restantes: <span style="color: red; font-weight: bold;">07</span>
            </p>
        </div>

        <footer style="margin-top: 80px; padding-bottom: 40px; text-align: center; border-top: 1px solid #1f2937;">
            <div style="margin: 30px 0; display: flex; justify-content: center; gap: 40px; opacity: 0.6;">
                <i class="fab fa-instagram fa-2x"></i>
                <i class="fab fa-youtube fa-2x"></i>
                <i class="fab fa-whatsapp fa-2x"></i>
            </div>
            <p style="font-size: 10px;">Este site não faz parte do Google ou do Facebook. Além disso, este site NÃO é endossado pelo Google ou Facebook em qualquer aspecto.</p>
        </footer>
    </div>

    <script>
        // Sistema de Notificações Fake
        const names = ["Ricardo", "Ana", "Juliana", "Carlos", "Beatriz", "Marcos", "Fernanda"];
        const cities = ["Belém", "São Paulo", "Icoaraci", "Curitiba", "Fortaleza", "Castanhal"];
        
        function showNotification() {
            const notif = document.getElementById('sale-notification');
            const text = document.getElementById('notification-text');
            const randomName = names[Math.floor(Math.random() * names.length)];
            const randomCity = cities[Math.floor(Math.random() * cities.length)];
            
            text.innerHTML = `<b>${randomName}</b> de ${randomCity} acabou de adquirir o PRO`;
            
            notif.style.transform = "translateY(0)";
            setTimeout(() => {
                notif.style.transform = "translateY(150%)";
            }, 4000);
        }

        setInterval(showNotification, 12000); // Mostra a cada 12 segundos
        setTimeout(showNotification, 3000); // Primeira mostra após 3s
    </script>

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