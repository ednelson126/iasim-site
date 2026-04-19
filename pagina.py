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
                --dark: #07090c;
                --surface: #12151c;
                --text-main: #f3f4f6;
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
                bottom: 20px;
                left: 20px;
                background: white;
                color: #111;
                padding: 12px 20px;
                border-radius: 12px;
                display: flex;
                align-items: center;
                gap: 12px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.5);
                z-index: 9999;
                transform: translateY(200%);
                transition: transform 0.6s cubic-bezier(0.23, 1, 0.32, 1);
                font-size: 13px;
                min-width: 250px;
            }

            .hero {
                padding: 80px 20px;
                text-align: center;
                background: radial-gradient(circle at center, #161b22 0%, var(--dark) 100%);
            }

            h1 {
                font-size: clamp(1.8rem, 5vw, 3.5rem);
                font-weight: 800;
                max-width: 850px;
                margin: 0 auto 20px;
                line-height: 1.1;
                letter-spacing: -1px;
            }

            .accent { color: var(--brand); }

            .video-wrapper {
                max-width: 800px;
                margin: -40px auto 60px;
                padding: 10px;
                background: rgba(255,255,255,0.03);
                border-radius: 24px;
                border: 1px solid rgba(255,255,255,0.1);
            }

            .video-container {
                position: relative;
                padding-bottom: 56.25%;
                height: 0;
                border-radius: 16px;
                overflow: hidden;
            }

            .video-container iframe {
                position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            }

            .section { padding: 60px 20px; max-width: 1100px; margin: auto; }

            .grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 30px;
            }

            .card {
                background: var(--surface);
                border-radius: 24px;
                border: 1px solid rgba(255,255,255,0.05);
                overflow: hidden;
                transition: 0.3s;
            }

            .card-img {
                width: 100%;
                height: 220px;
                object-fit: cover;
            }

            .card-body { padding: 25px; }
            .card-body h3 { margin-top: 0; color: var(--brand); }

            /* Ajuste nos Depoimentos para não cortar texto */
            .test-scroll {
                display: flex; gap: 20px; overflow-x: auto; padding: 20px 0; scrollbar-width: none;
            }

            .test-item {
                min-width: 320px;
                max-width: 320px;
                background: #1a1e26;
                padding: 25px;
                border-radius: 18px;
                border-bottom: 3px solid var(--brand);
                word-wrap: break-word;
                overflow-wrap: break-word;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
            }

            .user-info {
                display: flex; align-items: center; gap: 12px; margin-bottom: 15px;
            }

            .user-info img {
                width: 50px; height: 50px; border-radius: 50%; object-fit: cover;
                flex-shrink: 0;
            }

            .cta-box {
                text-align: center;
                padding: 100px 20px;
                background: #0d1117;
                border-radius: 40px;
                margin: 40px 20px;
            }

            .main-btn {
                background: var(--brand);
                color: #000;
                text-decoration: none;
                padding: 22px 60px;
                font-size: 1.3rem;
                font-weight: 800;
                border-radius: 14px;
                display: inline-block;
                transition: 0.3s;
            }

            footer {
                padding: 40px;
                text-align: center;
                font-size: 14px;
                color: #4b5563;
                border-top: 1px solid rgba(255,255,255,0.05);
            }
        </style>
    </head>
    <body>

    <div id="sale-notif">
        <i class="fas fa-check-circle" style="color: #00c853; font-size: 18px;"></i>
        <span id="notif-content">...</span>
    </div>

    <section class="hero">
        <h1>O Bot que cria <span class="accent">Roteiros e Conteúdos Virais</span> para você lucrar todos os dias.</h1>
        <p style="color: #94a3b8; font-size: 1.1rem; max-width: 600px; margin: auto;">Deixe a Inteligência Artificial criar sua estratégia enquanto você escala seu faturamento.</p>
    </section>

    <div class="video-wrapper">
        <div class="video-container">
            <iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ" frameborder="0" allowfullscreen></iframe>
        </div>
    </div>

    <div class="section">
        <h2 style="text-align:center; margin-bottom: 50px;">O que o IAsim Pró entrega</h2>
        <div class="grid">
            <div class="card">
                <img src="https://images.unsplash.com/photo-1488190211105-8b0e65b80b4e?auto=format&fit=crop&w=600&q=80" class="card-img" alt="Escrita de roteiros">
                <div class="card-body">
                    <h3>Roteiros Magnéticos</h3>
                    <p>Scripts otimizados com ganchos de retenção que forçam o espectador a assistir até o fim e engajar.</p>
                </div>
            </div>
            <div class="card">
                <img src="https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=600&q=80" class="card-img" alt="Análise de dados">
                <div class="card-body">
                    <h3>Análise de Tendências</h3>
                    <p>O bot identifica o que está em alta no mercado antes de todo mundo, mantendo você sempre no topo.</p>
                </div>
            </div>
            <div class="card">
                <img src="https://images.unsplash.com/photo-1557804506-669a67965ba0?auto=format&fit=crop&w=600&q=80" class="card-img" alt="Marketing e Vendas">
                <div class="card-body">
                    <h3>Copy para Vendas</h3>
                    <p>Transforme visualizações em dinheiro com chamadas para ação (CTAs) impossíveis de serem ignoradas.</p>
                </div>
            </div>
        </div>
    </div>

    <div class="section">
        <h2 style="text-align:center;">Resultados Reais</h2>
        <div class="test-scroll">
            <div class="test-item">
                <div class="user-info">
                    <img src="https://i.pravatar.cc/150?u=12">
                    <div><b>Ricardo Alencar</b><br><small>Criador de Conteúdo</small></div>
                </div>
                <p>"O bot gerou um roteiro que bateu 100k views em menos de 24h. O engajamento subiu de forma bizarro."</p>
            </div>
            <div class="test-item">
                <div class="user-info">
                    <img src="https://i.pravatar.cc/150?u=25">
                    <div><b>Julia Mendes</b><br><small>Social Media</small></div>
                </div>
                <p>"Ganhei horas de produtividade. Entrego cronogramas inteiros para meus clientes em poucos minutos."</p>
            </div>
            <div class="test-item">
                <div class="user-info">
                    <img src="https://i.pravatar.cc/150?u=male_bruno">
                    <div><b>Bruno Costa</b><br><small>Empreendedor</small></div>
                </div>
                <p>"As ideias de vídeos rápidos são o que mais trazem leads qualificados para o meu WhatsApp hoje."</p>
            </div>
        </div>
    </div>

    <div class="cta-box">
        <h2 style="font-size: 3.5rem; margin: 0;" class="accent">R$ 19,90</h2>
        <p style="margin: 20px 0 40px; opacity: 0.7;">Pagamento único. Acesso vitalício imediato.</p>
        <a href="https://t.me/Iasim_bot" class="main-btn">
            ATIVAR MEU ACESSO AGORA <i class="fas fa-rocket" style="margin-left: 10px;"></i>
        </a>
    </div>

    <footer>
        todos os direitos reservados a @IAsim Pró 2026.
    </footer>

    <script>
        // Banco de dados diversificado para notificações
        const buyers = [
            {n: "Rafael", c: "São Paulo"}, {n: "Beatriz", c: "Curitiba"},
            {n: "Thiago", c: "Fortaleza"}, {n: "Larissa", c: "Rio de Janeiro"},
            {n: "Gustavo", c: "Belo Horizonte"}, {n: "Aline", c: "Salvador"},
            {n: "Felipe", c: "Florianópolis"}, {n: "Camila", c: "Brasília"},
            {n: "Rodrigo", c: "Porto Alegre"}, {n: "Isabela", c: "Recife"}
        ];

        let lastIndex = -1;

        function showNotif() {
            const el = document.getElementById('sale-notif');
            const content = document.getElementById('notif-content');
            
            let randomIndex;
            do {
                randomIndex = Math.floor(Math.random() * buyers.length);
            } while (randomIndex === lastIndex);
            
            lastIndex = randomIndex;
            const buyer = buyers[randomIndex];
            
            content.innerHTML = `<b>${buyer.n}</b> (${buyer.c}) acabou de adquirir o IAsim Pró`;
            
            el.style.transform = "translateY(0)";
            setTimeout(() => {
                el.style.transform = "translateY(200%)";
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