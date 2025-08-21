from flask import Flask, request
import requests
import os
import threading
import logging
import tempfile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configurações
PAGE_TOKEN_BOCA = os.getenv('PAGE_TOKEN_BOCA')
INSTAGRAM_ACCOUNT_ID = '17841464327364824'
FACEBOOK_PAGE_ID = '213776928485804'
WORDPRESS_URL = "https://jornalvozdolitoral.com/wp-json/wp/v2/media/"

def criar_legenda_completa(data):
    """Monta a legenda no formato profissional para Reels."""
    try:
        post_data = data.get('post', {})
        
        titulo = post_data.get('post_title', '')
        titulo_formatado = f"🚨 **{titulo.upper()}**\n\n"
        
        resumo = post_data.get('post_excerpt', '')
        if not resumo:
            conteudo = post_data.get('post_content', '')
            resumo = conteudo[:200] + "..." if len(conteudo) > 200 else conteudo
        
        legenda = (
            f"{titulo_formatado}"
            f"@bocanotrombonelitoral\n\n"
            f"---\n\n"
            f"{resumo}\n\n"
            f"📲 Leia a matéria completa no link da bio!\n\n"
            f"#Noticias #LitoralNorte #SãoSebastião #Brasil"
        )
        
        return legenda
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar legenda: {str(e)}")
        return data.get('post', {}).get('post_title', '') + "\n\nLeia a matéria completa no site! 📖"

def get_image_url_from_wordpress(image_id):
    """Busca a URL da imagem no WordPress"""
    try:
        logger.info(f"📡 Buscando imagem {image_id} no WordPress...")
        response = requests.get(f"{WORDPRESS_URL}{image_id}", timeout=10)
        
        if response.status_code == 200:
            media_data = response.json()
            image_url = media_data.get('source_url')
            logger.info(f"✅ Imagem encontrada: {image_url}")
            return image_url
        else:
            logger.error(f"❌ Erro ao buscar imagem: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Erro na busca da imagem: {str(e)}")
        return None

def publicar_facebook(image_url, caption):
    """Publica IMAGEM no Facebook (como vídeo estático)"""
    try:
        logger.info("📤 Publicando no Facebook...")
        
        if not PAGE_TOKEN_BOCA:
            logger.error("❌ Token não configurado")
            return False
        
        # Usa a PRÓPRIA IMAGEM como vídeo (truque do Facebook)
        params = {
            'access_token': PAGE_TOKEN_BOCA,
            'description': caption,
            'url': image_url  # Facebook converte imagem em vídeo automaticamente
        }
        
        response = requests.post(
            f'https://graph.facebook.com/v23.0/{FACEBOOK_PAGE_ID}/videos',
            params=params,
            timeout=120
        )
        
        if response.status_code == 200:
            logger.info("🎉 ✅ CONTEÚDO PUBLICADO NO FACEBOOK!")
            return True
        else:
            logger.error(f"❌ Erro Facebook: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro na publicação Facebook: {str(e)}")
        return False

def publicar_instagram(image_url, caption):
    """Publica IMAGEM no Instagram"""
    try:
        logger.info("📤 Publicando no Instagram...")
        
        if not PAGE_TOKEN_BOCA:
            logger.error("❌ Token não configurado")
            return False
        
        # Passo 1: Criar objeto de mídia para FOTO
        create_params = {
            'access_token': PAGE_TOKEN_BOCA,
            'caption': caption,
            'image_url': image_url  # URL da imagem direto
        }
        
        create_response = requests.post(
            f'https://graph.facebook.com/v23.0/{INSTAGRAM_ACCOUNT_ID}/media',
            params=create_params,
            timeout=120
        )
        
        if create_response.status_code != 200:
            logger.error(f"❌ Erro ao criar mídia Instagram: {create_response.text}")
            return False
        
        creation_id = create_response.json().get('id')
        if not creation_id:
            logger.error("❌ Não foi possível obter ID de criação")
            return False
        
        logger.info(f"✅ Mídia Instagram criada: {creation_id}")
        
        # Passo 2: Publicar
        publish_params = {
            'access_token': PAGE_TOKEN_BOCA,
            'creation_id': creation_id
        }
        
        publish_response = requests.post(
            f'https://graph.facebook.com/v23.0/{INSTAGRAM_ACCOUNT_ID}/media_publish',
            params=publish_params,
            timeout=120
        )
        
        if publish_response.status_code == 200:
            logger.info("🎉 ✅ PUBLICADO NO INSTAGRAM!")
            return True
        else:
            logger.error(f"❌ Erro publicação Instagram: {publish_response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro Instagram: {str(e)}")
        return False

@app.route('/webhook-boca', methods=['POST'])
def handle_webhook():
    try:
        logger.info("📍 Recebendo dados do WordPress...")
        data = request.json
        
        post_meta = data.get('post_meta', {})
        thumbnail_id = post_meta.get('_thumbnail_id', [None])[0]
        
        if not thumbnail_id:
            logger.error("❌ Nenhum ID de imagem encontrado")
            return "❌ ID da imagem não encontrado", 400
        
        caption = criar_legenda_completa(data)
        
        image_url = get_image_url_from_wordpress(thumbnail_id)
        if not image_url:
            logger.error("❌ Não foi possível obter a URL da imagem")
            return "❌ Erro ao buscar imagem", 500
        
        def publicar_tudo():
            facebook_ok = publicar_facebook(image_url, caption)
            instagram_ok = publicar_instagram(image_url, caption)
            
            if facebook_ok and instagram_ok:
                logger.info("🎉 ✅ PUBLICADO EM AMBAS AS PLATAFORMAS!")
            else:
                logger.warning("⚠️ Publicação em uma das plataformas falhou")
        
        thread = threading.Thread(target=publicar_tudo)
        thread.start()
        
        return "✅ Recebido! Publicação em andamento...", 200
        
    except Exception as e:
        logger.error(f"❌ Erro: {str(e)}")
        return "Erro", 500

@app.route('/')
def home():
    return "🚀 Sistema Funcionando! Boca no Trombone - Publicador Automático", 200

if __name__ == '__main__':
    logger.info("✅ Servidor pronto!")
    app.run(host='0.0.0.0', port=10000)
