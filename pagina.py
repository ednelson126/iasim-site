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
        <title>IAsim Pró - O Motor de Conteúdo Viral</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&display=swap" rel="stylesheet">
        
        <style>
            :root {
                --brand: #00ff88;
                --dark: #05070a;
                --surface: #0f172a;
                --text-main: #f8fafc;
                --text-dim: #94a3b8;
            }

            body {
                font-family: 'Plus Jakarta Sans', sans-serif;
                background-color: var(--dark);
                color: var(--text-main);
                margin: 0;
                line-height: 1.6;
                overflow-x: hidden;
            }

            /* Notificação de Venda */
            #sale-notif {
                position: fixed;
                bottom: 25px;
                left: 20px;
                background: #ffffff;
                color: #0f172a;
                padding: 14px 22px;
                border-radius: 16px;
                display: flex;
                align-items: center;
                gap: 12px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.4);
                z-index: 10000;
                transform: translateY(250%);
                transition: transform 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
                font-size: 14px;
            }

            /* --- Hero Section --- */
            .hero {
                padding: 120px 20px 80px;
                text-align: center;
                background: radial-gradient(circle at 50% 0%, #1e293b 0%, var(--dark) 75%);
            }

            h1 {
                font-size: clamp(2rem, 6vw, 4rem);
                font-weight: 800;
                max-width: 950px;
                margin: 0 auto 25px;
                line-height: 1.1;
                letter-spacing: -2px;
            }

            .accent { color: var(--brand); }

            /* --- Vídeo VSL --- */
            .video-wrapper {
                max-width: 900px;
                margin: -40px auto 100px;
                padding: 12px;
                background: rgba(255,255,255,0.02);
                border-radius: 32px;
                border: 1px solid rgba(255,255,255,0.08);
            }

            .video-container {
                position: relative;
                padding-bottom: 56.25%;
                height: 0;
                border-radius: 20px;
                overflow: hidden;
                box-shadow: 0 40px 100px rgba(0,0,0,0.5);
            }

            .video-container iframe {
                position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none;
            }

            /* --- Seções Gerais --- */
            .section { padding: 100px 20px; max-width: 1200px; margin: auto; }
            h2.section-title { text-align: center; font-size: 2.5rem; margin-bottom: 60px; font-weight: 800; }

            /* --- Grid de Serviços --- */
            .grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 40px;
            }

            .card {
                background: var(--surface);
                border-radius: 28px;
                border: 1px solid rgba(255,255,255,0.05);
                overflow: hidden;
                transition: transform 0.3s ease;
            }

            .card:hover { transform: translateY(-12px); border-color: var(--brand); }

            .card-img { width: 100%; height: 240px; object-fit: cover; }
            .card-body { padding: 35px; }
            .card-body h3 { margin: 0 0 15px; color: var(--brand); font-size: 1.5rem; }

            /* --- Seção de Público-Alvo --- */
            .target-list {
                display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; margin-top: 40px;
            }

            .target-item {
                background: rgba(255,255,255,0.03);
                padding: 15px 30px;
                border-radius: 100px;
                border: 1px solid rgba(255,255,255,0.1);
                font-weight: 600;
            }

            /* --- DEPOIMENTOS CORRIGIDOS (TAMANHO REDUZIDO E SEM CORTE) --- */
            .test-scroll {
                display: flex; gap: 20px; overflow-x: auto; padding: 20px 10px 40px; scrollbar-width: none;
            }

            .test-item {
                min-width: 280px;
                max-width: 300px;
                background: #1e293b;
                padding: 25px;
                border-radius: 20px;
                border-bottom: 4px solid var(--brand);
                display: flex;
                flex-direction: column;
                height: auto;
                word-wrap: break-word;
                overflow-wrap: break-word;
            }

            .user-info { display: flex; align-items: center; gap: 12px; margin-bottom: 15px; }
            .user-info img {
                width: 50px; height: 50px; border-radius: 50%; object-fit: cover;
                border: 2px solid var(--brand);
                flex-shrink: 0;
            }

            .test-text { 
                font-style: italic; 
                color: #cbd5e1; 
                line-height: 1.4; 
                font-size: 14px; 
                margin: 0;
            }

            /* --- FAQ --- */
            .faq-container { max-width: 800px; margin: auto; }
            .faq-item { background: #111827; padding: 25px; border-radius: 15px; margin-bottom: 15px; border-left: 4px solid var(--brand); }

            /* --- CTA Area --- */
            .cta-box {
                text-align: center;
                padding: 120px 20px;
                background: linear-gradient(180deg, var(--dark) 0%, #020617 100%);
            }

            .main-btn {
                background: var(--brand);
                color: #000;
                text-decoration: none;
                padding: 28px 70px;
                font-size: 1.5rem;
                font-weight: 800;
                border-radius: 20px;
                display: inline-block;
                box-shadow: 0 25px 50px rgba(0, 255, 136, 0.2);
                transition: 0.3s;
            }

            footer {
                padding: 60px 20px;
                text-align: center;
                font-size: 14px;
                color: #475569;
                border-top: 1px solid rgba(255,255,255,0.05);
            }
        </style>
    </head>
    <body>

    <div id="sale-notif">
        <i class="fas fa-check-circle" style="color: #10b981; font-size: 20px;"></i>
        <span id="notif-content">...</span>
    </div>

    <section class="hero">
        <h1>O Bot que cria <span class="accent">Roteiros e Conteúdos Virais</span> para você lucrar todos os dias.</h1>
        <p style="color: var(--text-dim); font-size: 1.3rem; max-width: 750px; margin: auto;">Chega de bloqueio criativo. Tenha uma linha de produção de conteúdo automatizada em suas mãos.</p>
    </section>

    <div class="video-wrapper">
        <div class="video-container">
            <iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ" allowfullscreen></iframe>
        </div>
    </div>

    <div class="section">
        <h2 class="section-title">Engenharia de Conversão</h2>
        <div class="grid">
            <div class="card">
                <img src="https://images.unsplash.com/photo-1512486130939-2c4f79935e4f?auto=format&fit=crop&w=600&q=80" class="card-img" alt="Scripts">
                <div class="card-body">
                    <h3>Scripts Magnéticos</h3>
                    <p>Estruturas de roteiros validadas para TikTok, Reels e YouTube Shorts que garantem retenção acima da média.</p>
                </div>
            </div>
            <div class="card">
                <img src="https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=600&q=80" class="card-img" alt="Trends">
                <div class="card-body">
                    <h3>Trends em Tempo Real</h3>
                    <p>O bot monitora o que está viralizando e adapta seu nicho para surfar na onda antes da saturação.</p>
                </div>
            </div>
            <div class="card">
                <img src="https://images.unsplash.com/photo-1557838923-2985c318be48?auto=format&fit=crop&w=600&q=80" class="card-img" alt="Copywriting">
                <div class="card-body">
                    <h3>Copywriting de Elite</h3>
                    <p>Legendas e CTAs que não apenas informam, mas convertem curiosos em seguidores e compradores.</p>
                </div>
            </div>
        </div>
    </div>

    <div class="section">
        <h2 class="section-title">Resultados Reais</h2>
        <div class="test-scroll">
            <div class="test-item">
                <div class="user-info">
                    <img src="https://randomuser.me/api/portraits/men/32.jpg" alt="Ricardo">
                    <div><b>Ricardo Alencar</b><br><small>Produtor Digital</small></div>
                </div>
                <p class="test-text">"O bot gerou um roteiro que bateu 150k views em apenas 18 horas. Nunca vi nada tão preciso para prender a atenção do público."</p>
            </div>
            
            <div class="test-item">
                <div class="user-info">
                    <img src="https://randomuser.me/api/portraits/women/44.jpg" alt="Julia">
                    <div><b>Julia Mendes</b><br><small>Social Media</small></div>
                </div>
                <p class="test-text">"Parei de perder noites criando calendários. O IAsim Pró faz em 5 minutos o que eu levava 3 dias para estruturar."</p>
            </div>
            
            <div class="test-item">
                <div class="user-info">
                    <img src="https://randomuser.me/api/portraits/men/85.jpg" alt="Bruno">
                    <div><b>Bruno Costa</b><br><small>Afiliado Profissional</small></div>
                </div>
                <p class="test-text">"As CTAs desse bot são matadoras. Minha taxa de conversão no tráfego orgânico subiu 40% desde que comecei a usar o IAsim."</p>
            </div>
        </div>
    </div>

    <div class="section">
        <h2 class="section-title">Dúvidas Frequentes</h2>
        <div class="faq-container">
            <div class="faq-item"><b>O acesso é vitalício?</b><br>Sim. Você paga uma única vez e terá acesso para sempre, incluindo atualizações.</div>
            <div class="faq-item"><b>Funciona para qualquer nicho?</b><br>Sim. O bot foi treinado para se adaptar a qualquer área, desde saúde até marketing e entretenimento.</div>
            <div class="faq-item"><b>Preciso pagar mensalidade na IA?</b><br>Não. A estrutura do IAsim Pró é independente para que você não tenha custos ocultos.</div>
        </div>
    </div>

    <div class="cta-box">
        <h2 style="font-size: 4.5rem; margin: 0;" class="accent">R$ 19,90</h2>
        <p style="margin: 25px 0 50px; opacity: 0.8; font-size: 1.2rem;">Oferta por tempo limitado. Leve o pack completo hoje.</p>
        <a href="https://t.me/Iasim_bot" class="main-btn">
            QUERO O MEU ACESSO AGORA <i class="fas fa-chevron-right" style="margin-left: 15px;"></i>
        </a>
    </div>

    <footer>
        todos os direitos reservados a @IAsim Pró 2026.
    </footer>

    <script>
        const buyers = [
            {n: "Rafael", c: "São Paulo"}, {n: "Beatriz", c: "Curitiba"},
            {n: "Thiago", c: "Fortaleza"}, {n: "Larissa", c: "Porto Alegre"},
            {n: "Gustavo", c: "Belo Horizonte"}, {n: "Amanda", c: "Manaus"},
            {n: "Felipe", c: "Florianópolis"}, {n: "Mariana", c: "Recife"},
            {n: "Caio", c: "Cuiabá"}, {n: "Fernanda", c: "Vitória"}
        ];

        let currentIdx = 0;

        function showNotif() {
            const el = document.getElementById('sale-notif');
            const content = document.getElementById('notif-content');
            
            const buyer = buyers[currentIdx];
            currentIdx = (currentIdx + 1) % buyers.length;
            
            content.innerHTML = `<b>${buyer.n}</b> de ${buyer.c} acabou de ativar o IAsim Pró`;
            
            el.style.transform = "translateY(0)";
            setTimeout(() => {
                el.style.transform = "translateY(250%)";
            }, 4500);
        }

        setInterval(showNotif, 12000);
        setTimeout(showNotif, 3000);
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