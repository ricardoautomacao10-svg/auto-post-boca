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
FACEBOOK_PAGE_ID = os.getenv('FACEBOOK_PAGE_ID', '213776928485804')

# TEMPLATE INLINE (já existente)
template_html = """SEU_TEMPLATE_AQUI"""
template = Template(template_html)

def publish_to_instagram(titulo, imagem_url, hashtags):
    """Publica imagem no Instagram"""
    try:
        if not INSTAGRAM_ACCESS_TOKEN:
            return {"status": "error", "message": "❌ PAGE_TOKEN_BOCA não configurado"}
        if not INSTAGRAM_ACCOUNT_ID:
            return {"status": "error", "message": "❌ INSTAGRAM_ID não configurado"}
        
        create_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_ACCOUNT_ID}/media"
        payload = {
            'image_url': imagem_url,
            'caption': f"{titulo}\n\n{hashtags}\n\n@bocanotrombonelitoral",
            'access_token': INSTAGRAM_ACCESS_TOKEN
        }
        
        response = requests.post(create_url, data=payload, timeout=30)
        result = response.json()
        
        if 'id' not in result:
            return {"status": "error", "message": result}
        
        creation_id = result['id']
        
        publish_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_ACCOUNT_ID}/media_publish"
        publish_payload = {
            'creation_id': creation_id,
            'access_token': INSTAGRAM_ACCESS_TOKEN
        }
        
        publish_response = requests.post(publish_url, data=publish_payload, timeout=30)
        publish_result = publish_response.json()
        
        if 'id' in publish_result:
            return {"status": "success", "id": publish_result['id'], "message": "Imagem publicada com sucesso!"}
        else:
            return {"status": "error", "message": publish_result}
            
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.route('/webbook-boca', methods=['POST'])
def handle_webhook():
    try:
        data = request.json
        titulo = data.get('titulo', '')
        imagem_url = data.get('imagem_url', '')
        hashtags = data.get('hashtags', '')
        
        publication_result = publish_to_instagram(titulo, imagem_url, hashtags)
        
        if publication_result['status'] == 'success':
            return jsonify({
                "status": "success", 
                "message": "Imagem publicada com sucesso!",
                "instagram_id": publication_result['id']
            })
        else:
            return jsonify({
                "status": "error", 
                "message": f"Erro ao publicar: {publication_result['message']}"
            }), 500
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/')
def index():
    token_exists = bool(INSTAGRAM_ACCESS_TOKEN)
    account_exists = bool(INSTAGRAM_ACCOUNT_ID)
    
    return f"""
    <h1>Status do Sistema</h1>
    <p><b>PAGE_TOKEN_BOCA:</b> {token_exists and '✅ Configurado' or '❌ Não configurado'}</p>
    <p><b>INSTAGRAM_ID:</b> {account_exists and '✅ Configurado' or '❌ Não configurado'}</p>
    <p><b>Instagram Account:</b> {INSTAGRAM_ACCOUNT_ID}</p>
    <p><a href="/test-webhook">Testar publicação</a></p>
    """

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
