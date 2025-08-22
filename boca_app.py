from flask import Flask, request, jsonify
import os
import logging
import requests
import json
from jinja2 import Template
import time

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
    <title>Boca no Trombone - Post</title>
    <style>
        * { 
            margin: 0; 
            padding: 0; 
            box-sizing: border-box; 
        }
        
        body { 
            width: 1080px; 
            height: 1080px; 
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
            justify-content: center;
        }
        
        .header {
            width: 100%;
            background-color: #e60000;
            padding: 20px;
            text-align: center;
            font-weight: bold;
            font-size: 32px;
        }
        
        .image-container {
            width: 80%;
            height: 60%;
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 20px 0;
        }
        
        .news-image {
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
            border: 3px solid #fff;
            border-radius: 15px;
        }
        
        .headline-container {
            width: 90%;
            background-color: #fff;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        
        .headline {
            color: #000;
            font-weight: 800;
            font-size: 36px;
            text-align: center;
            line-height: 1.2;
        }
        
        .footer {
            width: 100%;
            text-align: center;
            font-size: 24px;
            font-weight: bold;
            padding: 10px;
        }
        
        .hashtag {
            color: #ffcc00;
            margin-top: 10px;
            font-size: 20px;
        }
        
        .fallback-text {
            color: white;
            font-size: 24px;
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
        
        <div class="footer">
            @bocanotrombonelitoral
            <div class="hashtag">{{ hashtags }}</div>
        </div>
    </div>
</body>
</html>
"""

template = Template(template_html)

def publish_to_instagram(titulo, imagem_url, hashtags):
    """Publica IMAGEM no Instagram Feed"""
    try:
        logger.info(f"📸 Publicando IMAGEM: {titulo}")
        
        # VERIFICAR SE AS VARIÁVEIS ESTÃO CONFIGURADAS
        if not INSTAGRAM_ACCESS_TOKEN:
            return {"status": "error", "message": "❌ PAGE_TOKEN_BOCA não configurado"}
        if not INSTAGRAM_ACCOUNT_ID:
            return {"status": "error", "message": "❌ INSTAGRAM_ID não configurado"}
        
        # 1. Criar container para IMAGEM
        create_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_ACCOUNT_ID}/media"
        
        payload = {
            'image_url': imagem_url,  # ⚡ IMAGEM (não vídeo)
            'caption': f"{titulo}\n\n{hashtags}\n\n@bocanotrombonelitoral",
            'access_token': INSTAGRAM_ACCESS_TOKEN
        }
        
        logger.info(f"📦 Criando container de IMAGEM...")
        response = requests.post(create_url, data=payload, timeout=30)
        result = response.json()
        
        if 'id' not in result:
            logger.error(f"❌ Erro ao criar container: {result}")
            return {"status": "error", "message": result}
        
        creation_id = result['id']
        logger.info(f"✅ Container de imagem criado: {creation_id}")
        
        # 2. Publicar a IMAGEM
        publish_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_ACCOUNT_ID}/media_publish"
        publish_payload = {
            'creation_id': creation_id,
            'access_token': INSTAGRAM_ACCESS_TOKEN
        }
        
        logger.info(f"🚀 Publicando IMAGEM no Instagram...")
        publish_response = requests.post(publish_url, data=publish_payload, timeout=30)
        publish_result = publish_response.json()
        
        if 'id' in publish_result:
            logger.info(f"🎉 IMAGEM PUBLICADA COM SUCESSO! ID: {publish_result['id']}")
            return {"status": "success", "id": publish_result['id'], "message": "Imagem publicada com sucesso!"}
        else:
            logger.error(f"❌ Erro na publicação: {publish_result}")
            return {"status": "error", "message": publish_result}
            
    except Exception as e:
        logger.error(f"💥 Erro grave na publicação: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.route('/webhook-boca', methods=['POST'])
def handle_webhook():
    """Endpoint para receber webhooks do WordPress - PARA IMAGENS"""
    try:
        data = request.json
        logger.info(f"🌐 Webhook recebido do WordPress")
        
        # Extrair dados do WordPress
        titulo = data.get('post', {}).get('post_title', 'Título da notícia')
        imagem_url = data.get('post_thumbnail', '')  # ⚡ IMAGEM da notícia
        
        # Extrair categoria e criar hashtags
        categorias = data.get('taxonomies', {}).get('category', {})
        categoria = list(categorias.keys())[0] if categorias else 'Geral'
        hashtags = f"#{categoria} #Noticias #LitoralNorte" if categoria else "#Noticias #LitoralNorte"
        
        # 🚀 PUBLICAR IMAGEM NO INSTAGRAM
        publication_result = publish_to_instagram(titulo, imagem_url, hashtags)
        
        if publication_result['status'] == 'success':
            logger.info(f"✅ Publicação concluída: {publication_result['id']}")
            return jsonify({
                "status": "success", 
                "message": "Imagem publicada com sucesso!",
                "instagram_id": publication_result['id'],
                "dados_recebidos": {
                    "titulo": titulo,
                    "imagem_url": imagem_url,
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
        <h1>🔧 Status do Sistema Boca no Trombone - IMAGENS</h1>
        <p><b>PAGE_TOKEN_BOCA:</b> {token_exists and '✅ Configurado' or '❌ Não configurado'}</p>
        <p><b>INSTAGRAM_ID:</b> {account_exists and '✅ Configurado' or '❌ Não configurado'}</p>
        <p><b>Instagram Account ID:</b> {INSTAGRAM_ACCOUNT_ID}</p>
        <p><b>Access Token (início):</b> {INSTAGRAM_ACCESS_TOKEN[:20] + '...' if INSTAGRAM_ACCESS_TOKEN else 'N/A'}</p>
        <br>
        <p><b>🚀 SISTEMA DE IMAGENS ATIVADO!</b></p>
        <p><b>📤 Endpoint Webhook:</b> <code>https://auto-post-boca.onrender.com/webhook-boca</code></p>
        <p><b>💡 Funcionamento:</b> Recebe imagens do WordPress e publica no Instagram</p>
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
    """Página para testar webhook manualmente - PARA IMAGENS"""
    if request.method == 'POST':
        # Dados de teste PARA IMAGEM
        test_data = {
            "post": {
                "post_title": "TESTE - Prefeitura de Caraguatatuba empossa nova comissão"
            },
            "post_thumbnail": "https://jornalvozdolitoral.com/wp-content/uploads/2025/08/image-64.png",
            "taxonomies": {
                "category": {
                    "caraguatatuba": {
                        "name": "Caraguatatuba"
                    }
                }
            }
        }
        
        # Chamar o webhook handler manualmente
        with app.test_client() as client:
            response = client.post('/webhook-boca', json=test_data)
        
        result = response.get_json()
        
        if result and result.get('status') == 'success':
            return f"""
            <h1>🎉 IMAGEM PUBLICADA COM SUCESSO!</h1>
            <p><b>ID do Instagram:</b> {result.get('instagram_id', 'N/A')}</p>
            <pre>{json.dumps(result, indent=2)}</pre>
            <p>✅ Verifique no <a href="https://www.instagram.com/bocanotrombonelitoral" target="_blank">Instagram</a> se a imagem apareceu!</p>
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
    <h1>🧪 Testar Publicação de IMAGEM</h1>
    <p><b>⚠️ ATENÇÃO:</b> Este teste vai publicar uma IMAGEM DE VERDADE no Instagram!</p>
    <form method="POST">
        <input type="submit" value="🚀 Publicar Imagem de Teste" style="padding: 15px; font-size: 16px; background: red; color: white; border: none; border-radius: 5px;">
    </form>
    <p><a href="/">🏠 Voltar ao início</a></p>
    """

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info("🚀 Sistema de IMAGENS 24x7 INICIADO!")
    app.run(host='0.0.0.0', port=port, debug=False)
