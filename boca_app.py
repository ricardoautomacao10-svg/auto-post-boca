from flask import Flask, request, jsonify
import os
import logging
import requests
import json
from jinja2 import Template
import tempfile
import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Variáveis de ambiente
INSTAGRAM_ACCESS_TOKEN = os.getenv('PAGE_TOKEN', '')
INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv('USER_ACCOUNT_ID', '')

# TEMPLATE INLINE (para evitar problemas com arquivo não encontrado)
template_html = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Boca no Trombone - Reel</title>
    <style>
        * { 
            margin: 0; 
            padding: 0; 
            box-sizing: border-box; 
        }
        
        body { 
            width: 1080px; 
            height: 1920px; 
            background-color: #000; 
            color: white; 
            position: relative; 
            overflow: hidden;
            font-family: Arial, sans-serif;
        }
        
        .container {
            width: 100%;
            height: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        
        .header {
            width: 100%;
            background-color: #e60000;
            padding: 30px;
            text-align: center;
            font-weight: bold;
            font-size: 42px;
        }
        
        .image-container {
            width: 100%;
            height: 50%;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 40px;
        }
        
        .news-image {
            max-width: 90%;
            max-height: 90%;
            object-fit: contain;
            border: 3px solid #fff;
            border-radius: 15px;
        }
        
        .headline-container {
            width: 90%;
            background-color: #fff;
            padding: 30px;
            border-radius: 15px;
            margin-top: 30px;
        }
        
        .headline {
            color: #000;
            font-weight: 800;
            font-size: 48px;
            text-align: center;
            line-height: 1.2;
        }
        
        .arrow {
            position: absolute;
            bottom: 100px;
            font-size: 80px;
            color: #ffcc00;
            animation: bounce 2s infinite;
        }
        
        .footer {
            position: absolute;
            bottom: 30px;
            width: 100%;
            text-align: center;
            font-size: 32px;
            font-weight: bold;
        }
        
        .hashtag {
            color: #ffcc00;
            margin-top: 15px;
        }
        
        @keyframes bounce {
            0%, 20%, 50%, 80%, 100% {transform: translateY(0);}
            40% {transform: translateY(-20px);}
            60% {transform: translateY(-10px);}
        }
        
        .fallback-text {
            color: white;
            font-size: 32px;
            text-align: center;
            padding: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">BOCA NO TROMBONE - ILHABELA</div>
        
        <div class="image-container">
            {% if imagem_url and imagem_url != '' %}
            <img src="{{ imagem_url }}" alt="Imagem da notícia" class="news-image">
            {% else %}
            <div class="fallback-text">IMAGEM FORNECIDA PELO WORDPRESS</div>
            {% endif %}
        </div>
        
        <div class="headline-container">
            <div class="headline">{{ titulo }}</div>
        </div>
        
        <div class="arrow">⬇️</div>
        
        <div class="footer">
            @bocanotrombonelitoral
            <div class="hashtag">{{ hashtags }}</div>
        </div>
    </div>
</body>
</html>
"""

template = Template(template_html)

@app.route('/webbook-boca', methods=['POST'])
def handle_webhook():
    """Endpoint para receber webhooks do WordPress"""
    try:
        data = request.json
        logger.info(f"Webhook recebido: {json.dumps(data)}")
        
        # Extrair dados da notícia
        titulo = data.get('titulo', 'Título da notícia')
        imagem_url = data.get('imagem_url', '')
        categoria = data.get('categoria', 'Geral')
        hashtags = data.get('hashtags', '#Noticias #LitoralNorte')
        
        # Gerar HTML do reel
        html_content = template.render(
            titulo=titulo,
            imagem_url=imagem_url,
            categoria=categoria,
            hashtags=hashtags
        )
        
        # SIMULAÇÃO - Em produção, você precisaria converter para vídeo
        logger.info(f"Reel gerado para: {titulo}")
        
        # SIMULAÇÃO - Em produção, aqui viria a publicação real
        # result = publish_to_instagram(titulo, hashtags)
        
        return jsonify({
            "status": "success", 
            "message": "Reel processado com sucesso (modo simulação)",
            "dados_recebidos": {
                "titulo": titulo,
                "imagem_url": imagem_url,
                "categoria": categoria,
                "hashtags": hashtags
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao processar webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

def publish_to_instagram(titulo, hashtags):
    """Simula publicação no Instagram (implementação real viria depois)"""
    # Esta é uma implementação simulada para testes
    logger.info(f"SIMULAÇÃO: Publicando no Instagram - {titulo} {hashtags}")
    return {"id": "simulado_123", "status": "success"}

@app.route('/')
def index():
    """Página inicial com status completo"""
    try:
        # Verificar se variáveis existem
        token_exists = bool(INSTAGRAM_ACCESS_TOKEN)
        business_id_exists = bool(INSTAGRAM_BUSINESS_ACCOUNT_ID)
        
        status_html = f"""
        <h1>🔧 Status do Sistema Boca no Trombone</h1>
        <p><b>Access Token:</b> {token_exists and '✅ Configurado' or '❌ Não configurado'}</p>
        <p><b>Business ID:</b> {business_id_exists and '✅ Configurado' or '❌ Não configurado'}</p>
        <p><b>Business Account ID:</b> {INSTAGRAM_BUSINESS_ACCOUNT_ID or 'N/A'}</p>
        <p><b>Access Token (início):</b> {INSTAGRAM_ACCESS_TOKEN[:20] + '...' if INSTAGRAM_ACCESS_TOKEN else 'N/A'}</p>
        <br>
        <p><b>⚠️ MODO SIMULAÇÃO ATIVADO:</b> O sistema recebe webhooks mas não publica ainda</p>
        <p><a href="/test-webhook">🧪 Testar webhook</a></p>
        """
        
        # Testar conexão com API se tokens existirem
        if token_exists and business_id_exists:
            try:
                test_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}?fields=name,instagram_business_account&access_token={INSTAGRAM_ACCESS_TOKEN}"
                response = requests.get(test_url, timeout=10)
                status = "✅" if response.status_code == 200 else "❌"
                status_html += f'<p><b>Conexão API:</b> {status} Código: {response.status_code}</p>'
            except Exception as e:
                status_html += f'<p><b>Conexão API:</b> ❌ Erro: {str(e)}</p>'
        
        return status_html
        
    except Exception as e:
        return f"<h1>❌ Erro na verificação:</h1><p>{str(e)}</p>"

@app.route('/test-webhook', methods=['GET', 'POST'])
def test_webhook():
    """Página para testar webhook manualmente"""
    if request.method == 'POST':
        # Simular dados de teste
        test_data = {
            "titulo": "TESTE - São Sebastião depois do caos, ônibus emergenciais começam a circular",
            "imagem_url": "https://jornalvozdolitoral.com/wp-content/uploads/2025/08/image-59.png",
            "categoria": "Urgente",
            "hashtags": "#SãoSebastião #Noticias #LitoralNorte"
        }
        
        # Chamar o webhook handler manualmente
        with app.test_client() as client:
            response = client.post('/webbook-boca', json=test_data)
        
        return f"""
        <h1>🧪 Teste de Webhook Realizado</h1>
        <pre>{json.dumps(response.get_json(), indent=2)}</pre>
        <p><a href="/test-webhook">↩️ Fazer outro teste</a></p>
        <p><a href="/">🏠 Voltar ao início</a></p>
        """
    
    return """
    <h1>🧪 Testar Webhook Manualmente</h1>
    <form method="POST">
        <p>Este teste simula um webhook do WordPress com dados de exemplo.</p>
        <input type="submit" value="🔘 Executar Teste" style="padding: 15px; font-size: 16px;">
    </form>
    <p><a href="/">🏠 Voltar ao início</a></p>
    """

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info("🚀 Sistema de automação de Reels iniciado!")
    app.run(host='0.0.0.0', port=port, debug=False)
