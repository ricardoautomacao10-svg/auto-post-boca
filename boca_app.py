from flask import Flask, request, jsonify
import os
import logging
import requests
import json
import re
import time

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
    from base64 import b64encode
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

def obter_imagem_original(post_id):
    """Obtém a imagem ORIGINAL da notícia"""
    try:
        # Buscar dados do post
        post_url = f"{WP_URL}/wp-json/wp/v2/posts/{post_id}"
        response = requests.get(post_url, headers=HEADERS_WP, timeout=15)
        
        if response.status_code != 200:
            logger.error("❌ Erro ao buscar post")
            return None
            
        post_data = response.json()
        
        # Tentar obter featured_media (imagem de destaque)
        featured_media_id = post_data.get('featured_media')
        if featured_media_id:
            media_url = f"{WP_URL}/wp-json/wp/v2/media/{featured_media_id}"
            media_response = requests.get(media_url, headers=HEADERS_WP, timeout=15)
            
            if media_response.status_code == 200:
                media_data = media_response.json()
                return media_data.get('source_url')
        
        # Se não encontrar, tentar extrair imagem do conteúdo
        content = post_data.get('content', {}).get('rendered', '')
        if 'wp-image-' in content:
            # Extrair URL da imagem do conteúdo HTML
            import re
            image_match = re.search(r'src="([^"]+\.(jpg|jpeg|png))"', content)
            if image_match:
                return image_match.group(1)
        
        return None
        
    except Exception as e:
        logger.error(f"💥 Erro ao buscar imagem original: {str(e)}")
        return None

@app.route('/webhook-boca', methods=['POST'])
def handle_webhook():
    """Endpoint para receber webhooks do WordPress"""
    try:
        data = request.json
        logger.info("🌐 Webhook recebido do WordPress")
        
        post_id = data.get('post_id')
        if not post_id:
            return jsonify({"status": "error", "message": "❌ post_id não encontrado"}), 400
        
        # 🖼️ PRIMEIRO: Tentar imagem post_social (se existir)
        imagem_post_social = f"{WP_URL}/wp-content/uploads/post_social_{post_id}.jpg"
        
        try:
            response = requests.head(imagem_post_social, timeout=5)
            if response.status_code == 200:
                logger.info(f"✅ Usando imagem post_social: {post_id}")
                imagem_url = imagem_post_social
            else:
                # 🖼️ SEGUNDA OPÇÃO: Buscar imagem ORIGINAL
                logger.info(f"🔍 Imagem post_social não encontrada, buscando original...")
                imagem_url = obter_imagem_original(post_id)
                
                if not imagem_url:
                    return jsonify({
                        "status": "error", 
                        "message": "Nenhuma imagem encontrada para a notícia"
                    }), 404
                    
        except:
            # 🖼️ SEGUNDA OPÇÃO: Buscar imagem ORIGINAL
            logger.info(f"🔍 Erro ao acessar post_social, buscando original...")
            imagem_url = obter_imagem_original(post_id)
            
            if not imagem_url:
                return jsonify({
                    "status": "error", 
                    "message": "Nenhuma imagem encontrada para a notícia"
                }), 404
        
        # 📝 Dados para publicação
        titulo = data.get('post', {}).get('post_title', 'Título da notícia')
        resumo = data.get('post', {}).get('post_excerpt', 'Resumo da notícia')
        titulo = limpar_html(titulo)
        resumo = limpar_html(resumo)
        
        legenda = f"{titulo}\n\n{resumo}\n\nLeia a matéria completa!\n\n#noticias #litoralnorte"
        
        # 🚀 PUBLICAR
        resultado = publicar_no_instagram(imagem_url, legenda)
        
        if resultado.get('status') == 'success':
            return jsonify({
                "status": "success",
                "message": "Publicação no Instagram realizada",
                "instagram_id": resultado.get('id'),
                "imagem_utilizada": imagem_url
            })
        else:
            return jsonify({
                "status": "error", 
                "message": "Erro na publicação",
                "erro": resultado
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
    <p><b>Estratégia:</b> Usa post_social OU imagem original</p>
    <p><b>Endpoint:</b> <code>/webhook-boca</code></p>
    """

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info("🚀 Sistema de automação INICIADO!")
    app.run(host='0.0.0.0', port=port, debug=False)
