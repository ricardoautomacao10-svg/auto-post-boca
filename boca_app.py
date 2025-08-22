from flask import Flask, request, jsonify
import os
import logging
import requests
import json
import re
import time
from base64 import b64encode

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ⚡ VARIÁVEIS PARA INSTAGRAM:
INSTAGRAM_ACCESS_TOKEN = os.getenv('PAGE_TOKEN_BOCA', '') or os.getenv('USER_ACCESS_TOKEN', '')
INSTAGRAM_ACCOUNT_ID = os.getenv('INSTAGRAM_ID', '17841464327364824')

# ⚡ VARIÁVEIS DO WORDPRESS:
WP_URL = os.getenv('MP_URL', 'https://jornalvozdolitoral.com')
WP_USER = os.getenv('MP_USER', '')
WP_PASSWORD = os.getenv('MP_PASSWORD', '')

# Configurar headers do WordPress
HEADERS_WP = {}
if WP_USER and WP_PASSWORD:
    credentials = f"{WP_USER}:{WP_PASSWORD}"
    token_wp = b64encode(credentials.encode())
    HEADERS_WP = {'Authorization': f'Basic {token_wp.decode("utf-8")}'}
    logger.info("✅ Configuração WordPress OK")
else:
    logger.warning("⚠️ Configuração WordPress incompleta")

def limpar_html(texto):
    """Remove tags HTML do texto"""
    if not texto:
        return ""
    texto_limpo = re.sub('<[^>]+>', '', texto)
    texto_limpo = texto_limpo.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')
    return texto_limpo.strip()

def publicar_no_instagram(url_imagem, legenda):
    """Publica IMAGEM no Instagram"""
    try:
        logger.info(f"📸 Publicando no Instagram")
        
        if not INSTAGRAM_ACCESS_TOKEN or not INSTAGRAM_ACCOUNT_ID:
            return {"status": "error", "message": "❌ Configuração Instagram incompleta"}
        
        # 1. Criar container para IMAGEM
        create_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_ACCOUNT_ID}/media"
        payload = {
            'image_url': url_imagem,
            'caption': legenda,
            'access_token': INSTAGRAM_ACCESS_TOKEN
        }
        
        logger.info("📦 Criando container Instagram...")
        response = requests.post(create_url, data=payload, timeout=30)
        result = response.json()
        
        if 'id' not in result:
            logger.error(f"❌ Erro Instagram container: {result}")
            return {"status": "error", "message": result}
        
        creation_id = result['id']
        logger.info(f"✅ Container Instagram criado: {creation_id}")
        
        # 2. Publicar a IMAGEM
        publish_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_ACCOUNT_ID}/media_publish"
        publish_payload = {
            'creation_id': creation_id,
            'access_token': INSTAGRAM_ACCESS_TOKEN
        }
        
        logger.info("🚀 Publicando no Instagram...")
        publish_response = requests.post(publish_url, data=publish_payload, timeout=30)
        publish_result = publish_response.json()
        
        if 'id' in publish_result:
            logger.info(f"🎉 Instagram OK! ID: {publish_result['id']}")
            return {"status": "success", "id": publish_result['id']}
        else:
            logger.error(f"❌ Erro Instagram publicação: {publish_result}")
            return {"status": "error", "message": publish_result}
            
    except Exception as e:
        logger.error(f"💥 Erro Instagram: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.route('/webhook-boca', methods=['POST'])
def handle_webhook():
    """Endpoint para receber webhooks do WordPress"""
    try:
        data = request.json
        logger.info("🌐 Webhook recebido do WordPress")
        
        post_id = data.get('post_id')
        if not post_id:
            return jsonify({"status": "error", "message": "❌ post_id não encontrado"}), 400
        
        # 🖼️ USAR IMAGEM ORIGINAL (não post_social)
        imagem_url = f"{WP_URL}/wp-content/uploads/post_social_{post_id}.jpg"
        
        # ⏰ AGUARDAR até a imagem ficar pronta (SEU sistema gera)
        logger.info(f"⏰ Aguardando imagem post_social_{post_id}.jpg ser gerada...")
        
        for tentativa in range(12):  # Tenta por 6 minutos (12 x 30 segundos)
            try:
                response = requests.head(imagem_url, timeout=5)
                if response.status_code == 200:
                    logger.info(f"✅ Imagem encontrada na tentativa {tentativa + 1}")
                    break
                else:
                    logger.info(f"⏳ Tentativa {tentativa + 1}: Imagem ainda não disponível")
            except Exception as e:
                logger.info(f"⏳ Tentativa {tentativa + 1}: Erro ao verificar imagem - {e}")
            
            time.sleep(30)  # Espera 30 segundos entre tentativas
        else:
            logger.error(f"❌ Imagem post_social_{post_id}.jpg não foi gerada após 6 minutos")
            return jsonify({
                "status": "error", 
                "message": f"Imagem post_social_{post_id}.jpg não foi gerada"
            }), 404
        
        # Dados para publicação
        titulo = data.get('post', {}).get('post_title', 'Título da notícia')
        resumo = data.get('post', {}).get('post_excerpt', 'Resumo da notícia')
        titulo = limpar_html(titulo)
        resumo = limpar_html(resumo)
        
        legenda = f"{titulo}\n\n{resumo}\n\nLeia a matéria completa!\n\n#noticias #litoralnorte"
        
        # 🚀 PUBLICAR
        resultado_instagram = publicar_no_instagram(imagem_url, legenda)
        
        if resultado_instagram.get('status') == 'success':
            return jsonify({
                "status": "success",
                "message": "Publicação no Instagram realizada",
                "instagram": resultado_instagram,
                "imagem_utilizada": imagem_url
            })
        else:
            return jsonify({
                "status": "error", 
                "message": "Erro na publicação",
                "instagram": resultado_instagram
            }), 500
        
    except Exception as e:
        logger.error(f"💥 Erro no webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/')
def index():
    """Página inicial com status"""
    instagram_ok = bool(INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_ACCOUNT_ID)
    
    return f"""
    <h1>🔧 Status do Sistema Boca no Trombone</h1>
    <p><b>Instagram:</b> {instagram_ok and '✅ Configurado' or '❌ Não configurado'}</p>
    <p><b>Modo:</b> Aguardando imagem post_social_XXXXX.jpg</p>
    <p><b>Endpoint:</b> <code>/webhook-boca</code></p>
    <p><b>Health Check:</b> <a href="/health">/health</a></p>
    """

@app.route('/health')
def health_check():
    """Health check para manter o sistema acordado"""
    return jsonify({
        "status": "active", 
        "service": "boca-no-trombone",
        "timestamp": time.time(),
        "instagram_configured": bool(INSTAGRAM_ACCESS_TOKEN)
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info("🚀 Sistema 24x7 INICIADO!")
    app.run(host='0.0.0.0', port=port, debug=False)
