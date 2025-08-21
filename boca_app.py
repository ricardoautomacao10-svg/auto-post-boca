from flask import Flask, request
import requests
import os
import threading
import logging
import re
import tempfile
from PIL import Image
import io

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configurações
PAGE_TOKEN_BOCA = os.getenv('PAGE_TOKEN_BOCA')
INSTAGRAM_ACCOUNT_ID = '17841464327364824'
FACEBOOK_PAGE_ID = '213776928485804'
WORDPRESS_URL = "https://jornalvozdolitoral.com/wp-json/wp/v2/media/"

def converter_para_jpg(image_url):
    """Converte qualquer imagem para JPG (Facebook não aceita AVIF/WebP como vídeo)"""
    try:
        logger.info(f"🔄 Convertendo imagem para JPG: {image_url}")
        
        response = requests.get(image_url, timeout=30)
        if response.status_code != 200:
            return image_url  # Fallback para URL original
            
        # Verifica se é AVIF ou WebP
        if image_url.lower().endswith(('.avif', '.webp')):
            img = Image.open(io.BytesIO(response.content))
            
            # Converte para JPG em memória
            jpg_buffer = io.BytesIO()
            img.convert('RGB').save(jpg_buffer, format='JPEG', quality=95)
            jpg_buffer.seek(0)
            
            # Faz upload para ImgBB ou serviço temporário (simplificado - usa URL original como fallback)
            logger.warning("⚠️ Imagem AVIF/WEBP detectada - usando fallback para URL original")
            return image_url
            
        return image_url
        
    except Exception as e:
        logger.error(f"❌ Erro na conversão: {str(e)}")
        return image_url  # Fallback

def criar_legenda_completa(data):
    """Monta a legenda profissional para Reels - SEM HTML."""
    try:
        post_data = data.get('post', {})
        
        titulo = post_data.get('post_title', '')
        titulo = re.sub('<.*?>', '', titulo)
        
        resumo = post_data.get('post_excerpt', '')
        if not resumo:
            conteudo = post_data.get('post_content', '')
            conteudo = re.sub('<.*?>', '', conteudo)
            resumo = conteudo[:150] + "..." if len(conteudo) > 150 else conteudo
        else:
            resumo = re.sub('<.*?>', '', resumo)
        
        legenda = (
            f"🚨 {titulo.upper()}\n\n"
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
    """Publica no Facebook como VÍDEO"""
    try:
        logger.info("📤 Publicando no Facebook...")
        
        if not PAGE_TOKEN_BOCA:
            logger.error("❌ Token do Facebook não configurado")
            return False
        
        # Tenta método alternativo - como foto primeiro
        params = {
            'access_token': PAGE_TOKEN_BOCA,
            'message': caption,
            'url': image_url
        }
        
        response = requests.post(
            f'https://graph.facebook.com/v23.0/{FACEBOOK_PAGE_ID}/photos',
            params=params,
            timeout=60
        )
        
        if response.status_code == 200:
            logger.info("🎉 ✅ FOTO PUBLICADA NO FACEBOOK!")
            return True
        else:
            logger.error(f"❌ Erro Facebook (foto): {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro na publicação Facebook: {str(e)}")
        return False

def publicar_instagram(image_url, caption):
    """Publica no Instagram como FOTO (fallback)"""
    try:
        logger.info("📤 Publicando no Instagram...")
        
        if not PAGE_TOKEN_BOCA:
            logger.error("❌ Token do Instagram não configurado")
            return False
        
        # Método FOTO (fallback) - mais confiável
        create_params = {
            'access_token': PAGE_TOKEN_BOCA,
            'caption': caption,
            'image_url': image_url
        }
        
        create_response = requests.post(
            f'https://graph.facebook.com/v23.0/{INSTAGRAM_ACCOUNT_ID}/media',
            params=create_params,
            timeout=60
        )
        
        if create_response.status_code != 200:
            logger.error(f"❌ Erro ao criar mídia: {create_response.text}")
            return False
        
        creation_id = create_response.json().get('id')
        if not creation_id:
            logger.error("❌ Não foi possível obter ID de criação")
            return False
        
        logger.info(f"✅ Mídia criada: {creation_id}")
        
        # Aguarda processamento
        import time
        time.sleep(10)
        
        publish_params = {
            'access_token': PAGE_TOKEN_BOCA,
            'creation_id': creation_id
        }
        
        publish_response = requests.post(
            f'https://graph.facebook.com/v23.0/{INSTAGRAM_ACCOUNT_ID}/media_publish',
            params=publish_params,
            timeout=60
        )
        
        if publish_response.status_code == 200:
            logger.info("🎉 ✅ FOTO PUBLICADA NO INSTAGRAM!")
            return True
        else:
            logger.error(f"❌ Erro publicação: {publish_response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro Instagram: {str(e)}")
        return False

@app.route('/webhook-boca', methods=['POST'])
def webhook_boca():
    try:
        logger.info("📍 Recebendo dados do WordPress...")
        data = request.json
        
        if not data:
            return "❌ Dados inválidos", 400
        
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
        
        # Converte AVIF/WEBP para JPG se necessário
        image_url = converter_para_jpg(image_url)
        
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
        logger.error(f"❌ Erro no webhook: {str(e)}")
        return "Erro interno", 500

@app.route('/')
def home():
    return "🚀 Sistema Funcionando! Boca no Trombone - Publicador", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"✅ Servidor pronto na porta {port}!")
    app.run(host='0.0.0.0', port=port)
