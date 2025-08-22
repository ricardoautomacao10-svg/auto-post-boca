from flask import Flask, request, jsonify
import os
import logging
import requests
import json
from jinja2 import Template

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ⚡ VARIÁVEIS CORRETAS para SEU RENDER:
INSTAGRAM_ACCESS_TOKEN = os.getenv('PAGE_TOKEN_BOCA', '') or os.getenv('USER_ACCESS_TOKEN', '')
INSTAGRAM_ACCOUNT_ID = os.getenv('INSTAGRAM_ID', '17841464327364824')

# TEMPLATE INLINE
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
            fontWeight: 800;
            fontSize: 48px;
            textAlign: center;
            lineHeight: 1.2;
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
            {% if video_url and video_url != '' %}
            <video width="90%" height="90%" controls class="news-image">
                <source src="{{ video_url }}" type="video/mp4">
                Seu navegador não suporta vídeos.
            </video>
            {% else %}
            <div class="fallback-text">VÍDEO FORNECIDO PELO WORDPRESS</div>
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

def publish_to_instagram(titulo, video_url, hashtags):
    """Publica VÍDEO no Instagram (Reels)"""
    try:
        logger.info(f"🎬 Publicando VÍDEO no Reels: {titulo}")
        
        # VERIFICAR SE AS VARIÁVEIS ESTÃO CONFIGURADAS
        if not INSTAGRAM_ACCESS_TOKEN:
            return {"status": "error", "message": "❌ PAGE_TOKEN_BOCA não configurado"}
        if not INSTAGRAM_ACCOUNT_ID:
            return {"status": "error", "message": "❌ INSTAGRAM_ID não configurado"}
        
        # 1. Criar container para VÍDEO (REELS)
        create_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_ACCOUNT_ID}/media"
        
        payload = {
            'media_type': 'REELS',  # ⚡ IMPORTANTE: Especificar que é REELS
            'video_url': video_url,  # ⚡ URL do VÍDEO
            'caption': f"{titulo}\n\n{hashtags}\n\n@bocanotrombonelitoral",
            'access_token': INSTAGRAM_ACCESS_TOKEN
        }
        
        logger.info(f"📦 Criando container de VÍDEO...")
        response = requests.post(create_url, data=payload, timeout=30)
        result = response.json()
        
        if 'id' not in result:
            logger.error(f"❌ Erro ao criar container: {result}")
            return {"status": "error", "message": result}
        
        creation_id = result['id']
        logger.info(f"✅ Container de vídeo criado: {creation_id}")
        
        # 2. Publicar o VÍDEO (REELS)
        publish_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_ACCOUNT_ID}/media_publish"
        publish_payload = {
            'creation_id': creation_id,
            'access_token': INSTAGRAM_ACCESS_TOKEN
        }
        
        logger.info(f"🚀 Publicando REELS no Instagram...")
        publish_response = requests.post(publish_url, data=publish_payload, timeout=30)
        publish_result = publish_response.json()
        
        if 'id' in publish_result:
            logger.info(f"🎉 REELS PUBLICADO COM SUCESSO! ID: {publish_result['id']}")
            return {"status": "success", "id": publish_result['id'], "message": "Reel publicado com sucesso!"}
        else:
            logger.error(f"❌ Erro na publicação: {publish_result}")
            return {"status": "error", "message": publish_result}
            
    except Exception as e:
        logger.error(f"💥 Erro grave na publicação: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.route('/webhook-boca', methods=['POST'])
def handle_webhook():
    """Endpoint para receber webhooks do WordPress - VERSÃO PARA VÍDEOS"""
    try:
        data = request.json
        logger.info(f"🌐 Webhook recebido: {json.dumps(data)}")
        
        # Extrair dados da notícia
        titulo = data.get('titulo', 'Título do vídeo')
        video_url = data.get('video_url', '')  # ⚡ AGORA É video_url
        categoria = data.get('categoria', 'Geral')
        hashtags = data.get('hashtags', '#Noticias #LitoralNorte')
        
        # 🚀 PUBLICAR VÍDEO NO INSTAGRAM (REELS)
        publication_result = publish_to_instagram(titulo, video_url, hashtags)
        
        if publication_result['status'] == 'success':
            logger.info(f"✅ Publicação concluída: {publication_result['id']}")
            return jsonify({
                "status": "success", 
                "message": "Reel publicado com sucesso!",
                "instagram_id": publication_result['id'],
                "dados_recebidos": {
                    "titulo": titulo,
                    "video_url": video_url,
                    "categoria": categoria,
                    "hashtags": hashtags
                }
            })
        else:
            logger.error(f"❌ Falha na publicação: {publication_result['message']}")
            return jsonify({
                "status": "error", 
                "message": f"Erro ao publicar: {publication_result['message']}"
            }), 500
        
    except Exception as e:
        logger.error(f"💥 Erro ao processar webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/')
def index():
    """Página inicial com status completo"""
    try:
        # Verificar se variáveis existem
        token_exists = bool(INSTAGRAM_ACCESS_TOKEN)
        account_exists = bool(INSTAGRAM_ACCOUNT_ID)
        
        status_html = f"""
        <h1>🔧 Status do Sistema Boca no Trombone - REELS</h1>
        <p><b>PAGE_TOKEN_BOCA:</b> {token_exists and '✅ Configurado' or '❌ Não configurado'}</p>
        <p><b>INSTAGRAM_ID:</b> {account_exists and '✅ Configurado' or '❌ Não configurado'}</p>
        <p><b>Instagram Account ID:</b> {INSTAGRAM_ACCOUNT_ID}</p>
        <p><b>Access Token (início):</b> {INSTAGRAM_ACCESS_TOKEN[:20] + '...' if INSTAGRAM_ACCESS_TOKEN else 'N/A'}</p>
        <br>
        <p><b>🚀 SISTEMA DE REELS ATIVADO!</b></p>
        <p><b>📤 Endpoint Webhook:</b> <code>https://auto-post-boca.onrender.com/webbook-boca</code></p>
        <p><a href="/test-webhook">🧪 Testar publicação de REELS</a></p>
        """
        
        # Testar conexão com API se tokens existirem
        if token_exists and account_exists:
            try:
                test_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_ACCOUNT_ID}?fields=name,username&access_token={INSTAGRAM_ACCESS_TOKEN}"
                response = requests.get(test_url, timeout=10)
                status = "✅" if response.status_code == 200 else "❌"
                status_html += f'<p><b>Conexão API:</b> {status} Código: {response.status_code}</p>'
                
                # Mostrar dados da conta se funcionar
                if response.status_code == 200:
                    account_data = response.json()
                    status_html += f'<p><b>Conta Instagram:</b> {account_data.get("name")} (@{account_data.get("username")})</p>'
                    
            except Exception as e:
                status_html += f'<p><b>Conexão API:</b> ❌ Erro: {str(e)}</p>'
        
        return status_html
        
    except Exception as e:
        return f"<h1>❌ Erro na verificação:</h1><p>{str(e)}</p>"

@app.route('/test-webhook', methods=['GET', 'POST'])
def test_webhook():
    """Página para testar webhook manualmente - AGORA PUBLICA REELS!"""
    if request.method == 'POST':
        # Dados de teste PARA VÍDEO
        test_data = {
            "titulo": "TESTE REAL - REELS São Sebastião depois do caos",
            "video_url": "https://exemplo.com/video.mp4",  # ⚡ URL de um vídeo de teste
            "categoria": "Urgente",
            "hashtags": "#SãoSebastião #Noticias #LitoralNorte #BocaNoTrombone"
        }
        
        # Chamar o webhook handler manualmente
        with app.test_client() as client:
            response = client.post('/webbook-boca', json=test_data)
        
        result = response.get_json()
        
        if result and result.get('status') == 'success':
            return f"""
            <h1>🎉 REELS PUBLICADO COM SUCESSO!</h1>
            <p><b>ID do Instagram:</b> {result.get('instagram_id', 'N/A')}</p>
            <pre>{json.dumps(result, indent=2)}</pre>
            <p>✅ Verifique no <a href="https://www.instagram.com/bocanotrombonelitoral" target="_blank">Instagram</a> se o REEL apareceu!</p>
            <p><a href="/test-webhook">↩️ Fazer outro teste</a></p>
            <p><a href="/">🏠 Voltar ao início</a></p>
            """
        else:
            return f"""
            <h1>❌ ERRO NA PUBLICAÇÃO</h1>
            <pre>{json.dumps(result, indent=2)}</pre>
            <p><a href="/test-webhook">↩️ Tentar novamente</a></p>
            <p><a href="/">🏠 Voltar ao início</a></p>
            """
    
    return """
    <h1>🧪 Testar Publicação de REELS</h1>
    <p><b>⚠️ ATENÇÃO:</b> Este teste vai publicar um REEL DE VERDADE no Instagram!</p>
    <form method="POST">
        <input type="submit" value="🚀 Publicar REEL de Teste" style="padding: 15px; font-size: 16px; background: red; color: white; border: none; border-radius: 5px;">
    </form>
    <p><a href="/">🏠 Voltar ao início</a></p>
    """

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info("🚀 Sistema de REELS 24x7 INICIADO!")
    app.run(host='0.0.0.0', port=port, debug=False)
