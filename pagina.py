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
        <title>IAsim PRO | O Império da IA</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;700;900&display=swap" rel="stylesheet">
        
        <style>
            :root {
                --primary: #00ff88;
                --bg: #030508;
                --card: #0b1118;
                --glass: rgba(255, 255, 255, 0.03);
            }

            body {
                font-family: 'Outfit', sans-serif;
                background: var(--bg);
                color: #ffffff;
                margin: 0;
                scroll-behavior: smooth;
            }

            /* --- HEADER & HERO --- */
            header {
                padding: 100px 20px 60px;
                background: radial-gradient(circle at 50% 0%, #112240 0%, var(--bg) 70%);
                text-align: center;
            }

            .badge-ai {
                background: linear-gradient(90deg, #00ff88, #3b82f6);
                padding: 8px 20px;
                border-radius: 100px;
                font-size: 12px;
                font-weight: 900;
                letter-spacing: 2px;
                display: inline-block;
                margin-bottom: 30px;
                box-shadow: 0 0 20px rgba(0, 255, 136, 0.3);
            }

            h1 {
                font-size: clamp(2rem, 5vw, 4rem);
                font-weight: 900;
                line-height: 1.1;
                max-width: 900px;
                margin: 0 auto 20px;
            }

            /* --- SEÇÃO ENTREGÁVEIS (RECHEIO) --- */
            .deliverables {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 25px;
                padding: 50px 20px;
                max-width: 1100px;
                margin: auto;
            }

            .module-card {
                background: var(--card);
                border: 1px solid rgba(255,255,255,0.05);
                padding: 40px;
                border-radius: 30px;
                position: relative;
                overflow: hidden;
            }

            .module-card::before {
                content: '';
                position: absolute;
                top: 0; left: 0; width: 100%; height: 4px;
                background: linear-gradient(90deg, transparent, var(--primary), transparent);
            }

            /* --- DEPOIMENTOS ESTILO FEED --- */
            .testimonial-wall {
                background: #080c12;
                padding: 80px 20px;
            }

            .testimonial-grid {
                display: flex;
                overflow-x: auto;
                gap: 20px;
                padding: 20px;
                scrollbar-width: none;
            }

            .test-card {
                min-width: 320px;
                background: var(--glass);
                padding: 30px;
                border-radius: 20px;
                border: 1px solid rgba(255,255,255,0.1);
            }

            /* --- BOTÃO ULTRA --- */
            .cta-area {
                text-align: center;
                padding: 100px 20px;
                background: linear-gradient(180deg, var(--bg) 0%, #0a192f 100%);
            }

            .ultra-btn {
                background: #ffffff;
                color: #000;
                padding: 30px 60px;
                font-size: 1.5rem;
                font-weight: 900;
                border-radius: 100px;
                text-decoration: none;
                display: inline-block;
                transition: 0.3s;
                box-shadow: 0 10px 40px rgba(255,255,255,0.2);
            }

            .ultra-btn:hover {
                transform: translateY(-5px) scale(1.02);
                box-shadow: 0 20px 60px rgba(0, 255, 136, 0.4);
                background: var(--primary);
            }

            .price-tag {
                font-size: 5rem;
                font-weight: 900;
                margin: 20px 0;
                background: linear-gradient(180deg, #fff 30%, #444 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
        </style>
    </head>
    <body>

    <header>
        <div class="badge-ai">PRODUTO ATUALIZADO V2.0</div>
        <h1>TRANSFORME SUA <span style="color: var(--primary)">INTELIGÊNCIA</span> EM UMA MÁQUINA DE DINHEIRO.</h1>
        <p style="opacity: 0.7; font-size: 1.2rem; max-width: 700px; margin: 20px auto;">Acesse a estrutura que os grandes players usam para criar, postar e vender 10x mais rápido que qualquer humano.</p>
        
        <div style="margin-top: 50px; border-radius: 20px; border: 8px solid var(--glass); display: inline-block; width: 100%; max-width: 850px;">
            <div style="padding-bottom:56.25%; position:relative;">
                <iframe style="position:absolute; top:0; left:0; width:100%; height:100%; border-radius: 12px;" src="https://www.youtube.com/embed/dQw4w9WgXcQ" frameborder="0" allowfullscreen></iframe>
            </div>
        </div>
    </header>

    <div class="deliverables">
        <div class="module-card">
            <i class="fas fa-robot fa-3x" style="color: var(--primary)"></i>
            <h3>01. O Cérebro do Bot</h3>
            <p>Você recebe os Prompts Mestre. Não é o que você pergunta à IA, é COMO você pergunta. Gere roteiros que hipnotizam o público.</p>
        </div>
        <div class="module-card">
            <i class="fas fa-video fa-3x" style="color: var(--primary)"></i>
            <h3>02. Edição Sem Toque</h3>
            <p>Nossa lista de ferramentas que criam o vídeo para você. Basta colar o texto e a IA gera imagens, voz e legenda.</p>
        </div>
        <div class="module-card">
            <i class="fas fa-money-bill-wave fa-3x" style="color: var(--primary)"></i>
            <h3>03. Funil de Conversão</h3>
            <p>Como transformar visualizações em PIX. A estratégia de tráfego orgânico para quem não quer gastar 1 real com anúncios.</p>
        </div>
    </div>

    <div class="testimonial-wall">
        <h2 style="text-align: center; margin-bottom: 50px;">O QUE DIZEM QUEM JÁ ESTÁ NO TOPO</h2>
        <div class="testimonial-grid">
            <div class="test-card">
                <p>"Em 3 dias eu criei o conteúdo do mês inteiro. O IAsim PRO salvou minha agência."</p>
                <b>- Felipe S. (Gestor de Tráfego)</b>
            </div>
            <div class="test-card" style="border-color: var(--primary)">
                <p>"Antes eu perdia 4 horas pra postar 1 vídeo. Hoje o bot faz tudo e eu só clico em publicar. Faturamento dobrou em 15 dias!"</p>
                <b>- Mariana L. (Influencer Digital)</b>
            </div>
            <div class="test-card">
                <p>"Minha maior dúvida era se iniciantes conseguiam. O passo a passo é tão simples que minha avó faria."</p>
                <b>- João Pedro (Estudante)</b>
            </div>
        </div>
    </div>

    <div class="cta-area">
        <h3>ESTÁ PRONTO PARA O PRÓXIMO NÍVEL?</h3>
        <p>Acesso vitalício + Todas as atualizações futuras inclusas.</p>
        
        <div class="price-tag">R$ 19,90</div>
        
        <a href="https://t.me/Iasim_bot" class="ultra-btn">
            QUERO DOMINAR A IA AGORA <i class="fas fa-chevron-right" style="margin-left: 10px;"></i>
        </a>
        
        <div style="margin-top: 40px; display: flex; justify-content: center; gap: 30px; opacity: 0.5;">
            <span><i class="fas fa-shield-alt"></i> Compra Segura</span>
            <span><i class="fas fa-history"></i> Acesso Imediato</span>
            <span><i class="fas fa-undo"></i> 7 Dias de Garantia</span>
        </div>
    </div>

    <div style="max-width: 800px; margin: 80px auto; padding: 0 20px;">
        <h2 style="text-align: center;">PERGUNTAS FREQUENTES</h2>
        <div style="background: var(--card); border-radius: 20px; padding: 20px;">
            <p><b>Preciso de algum conhecimento prévio?</b><br>Absolutamente não. O IAsim PRO foi desenhado para quem nunca abriu uma ferramenta de IA na vida.</p>
            <hr style="opacity: 0.1; margin: 20px 0;">
            <p><b>O pagamento é mensal?</b><br>Não! O pagamento é ÚNICO. Você paga R$ 19,90 uma vez e o acesso é seu para sempre.</p>
            <hr style="opacity: 0.1; margin: 20px 0;">
            <p><b>E se eu não gostar?</b><br>Basta nos enviar um e-mail em até 7 dias e devolvemos 100% do seu investimento, sem burocracia.</p>
        </div>
    </div>

    <footer style="text-align: center; padding: 40px; font-size: 11px; opacity: 0.4;">
        &copy; 2026 IAsim PRO. CNPJ: 00.000.000/0001-00 <br>
        Este site não é do Facebook. Este site não é do Google.
    </footer>

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