from flask import Flask, request, jsonify
import os
import logging
import requests
import json
import re
from base64 import b64encode

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ⚡ VARIÁVEIS PARA INSTAGRAM:
INSTAGRAM_ACCESS_TOKEN = os.getenv('PAGE_TOKEN_BOCA', '') or os.getenv('USER_ACCESS_TOKEN', '')
INSTAGRAM_ACCOUNT_ID = os.getenv('INSTAGRAM_ID', '17841464327364824')

# ⚡ VARIÁVEIS PARA FACEBOOK:
FACEBOOK_ACCESS_TOKEN = os.getenv('PAGE_TOKEN_BOCA', '') or os.getenv('USER_ACCESS_TOKEN', '')
FACEBOOK_PAGE_ID = os.getenv('FACEBOOK_PAGE_ID', '213776928485804')

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
    # Remove tags HTML
    texto_limpo = re.sub('<[^>]+>', '', texto)
    # Substitui entidades HTML
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

def publicar_no_facebook(url_imagem, legenda):
    """Publica IMAGEM no Facebook"""
    try:
        logger.info(f"📘 Publicando no Facebook")
        
        if not FACEBOOK_ACCESS_TOKEN or not FACEBOOK_PAGE_ID:
            return {"status": "error", "message": "❌ Configuração Facebook incompleta"}
        
        # Publicar diretamente no Facebook
        publish_url = f"https://graph.facebook.com/v18.0/{FACEBOOK_PAGE_ID}/photos"
        payload = {
            'url': url_imagem,
            'message': legenda,
            'access_token': FACEBOOK_ACCESS_TOKEN
        }
        
        logger.info("🚀 Publicando no Facebook...")
        response = requests.post(publish_url, data=payload, timeout=30)
        result = response.json()
        
        if 'id' in result:
            logger.info(f"🎉 Facebook OK! ID: {result['id']}")
            return {"status": "success", "id": result['id']}
        else:
            logger.error(f"❌ Erro Facebook: {result}")
            return {"status": "error", "message": result}
            
    except Exception as e:
        logger.error(f"💥 Erro Facebook: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.route('/webhook-boca', methods=['POST'])
def handle_webhook():
    """Endpoint para receber webhooks do WordPress"""
    try:
        data = request.json
        logger.info("🌐 Webhook recebido do WordPress")
        
        # Extrair post_id do webhook
        post_id = data.get('post_id')
        if not post_id:
            return jsonify({"status": "error", "message": "❌ post_id não encontrado"}), 400
        
        # URL da imagem pronta (post_social_ID.jpg)
        imagem_url = f"{WP_URL}/wp-content/uploads/post_social_{post_id}.jpg"
        
        # Se não tiver config do WordPress, usar dados simples do webhook
        if not HEADERS_WP:
            titulo = data.get('post', {}).get('post_title', 'Título da notícia')
            resumo = data.get('post', {}).get('post_excerpt', 'Resumo da notícia')
            titulo = limpar_html(titulo)
            resumo = limpar_html(resumo)
        else:
            # Buscar dados do post no WordPress
            post_url = f"{WP_URL}/wp-json/wp/v2/posts/{post_id}"
            response = requests.get(post_url, headers=HEADERS_WP, timeout=15)
            
            if response.status_code != 200:
                return jsonify({"status": "error", "message": "❌ Erro ao buscar post"}), 500
            
            post_data = response.json()
            
            # Extrair título e resumo (sem BeautifulSoup)
            titulo = limpar_html(post_data.get('title', {}).get('rendered', ''))
            resumo = limpar_html(post_data.get('excerpt', {}).get('rendered', ''))
        
        # Criar legenda
        legenda = f"{titulo}\n\n{resumo}\n\nLeia a matéria completa em nosso site. Link na bio!\n\n#noticias #litoralnorte #brasil #jornalismo"
        
        # 🚀 PUBLICAR NAS DUAS REDES
        resultado_instagram = publicar_no_instagram(imagem_url, legenda)
        resultado_facebook = publicar_no_facebook(imagem_url, legenda)
        
        # Verificar resultados
        sucesso_instagram = resultado_instagram.get('status') == 'success'
        sucesso_facebook = resultado_facebook.get('status') == 'success'
        
        if sucesso_instagram or sucesso_facebook:
            return jsonify({
                "status": "success",
                "message": "Publicação realizada",
                "instagram": resultado_instagram,
                "facebook": resultado_facebook
            })
        else:
            return jsonify({
                "status": "error", 
                "message": "Erro nas publicações",
                "instagram": resultado_instagram,
                "facebook": resultado_facebook
            }), 500
        
    except Exception as e:
        logger.error(f"💥 Erro no webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/')
def index():
    """Página inicial com status"""
    instagram_ok = bool(INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_ACCOUNT_ID)
    facebook_ok = bool(FACEBOOK_ACCESS_TOKEN and FACEBOOK_PAGE_ID)
    wp_ok = bool(WP_USER and WP_PASSWORD)
    
    return f"""
    <h1>🔧 Status do Sistema Boca no Trombone</h1>
    <p><b>Instagram:</b> {instagram_ok and '✅ Configurado' or '❌ Não configurado'}</p>
    <p><b>Facebook:</b> {facebook_ok and '✅ Configurado' or '❌ Não configurado'}</p>
    <p><b>WordPress:</b> {wp_ok and '✅ Configurado' or '❌ Não configurado'}</p>
    <p><b>Endpoint:</b> <code>/webhook-boca</code></p>
    """

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info("🚀 Sistema de automação INICIADO!")
    app.run(host='0.0.0.0', port=port, debug=False)
