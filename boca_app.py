from flask import Flask, request
import requests
import os
import threading
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configurações
PAGE_TOKEN_BOCA = os.getenv('PAGE_TOKEN_BOCA')
INSTAGRAM_ACCOUNT_ID = '17841464327364824'
FACEBOOK_PAGE_ID = '213776928485804'
WORDPRESS_URL = "https://jornalvozdolitoral.com/wp-json/wp/v2/media/"

def criar_legenda_completa(data):
    """Monta a legenda profissional para Reels."""
    try:
        post_data = data.get('post', {})
        
        titulo = post_data.get('post_title', '')
        titulo = re.sub('<.*?>', '', titulo)
        titulo = titulo.replace('&nbsp;', ' ').replace('&#8217;', "'").replace(':', ' -')
        
        resumo = post_data.get('post_excerpt', '')
        if not resumo:
            conteudo = post_data.get('post_content', '')
            conteudo = re.sub('<.*?>', '', conteudo)
            conteudo = conteudo.replace('&nbsp;', ' ').replace('&#8217;', "'")
            resumo = conteudo[:120] + "..." if len(conteudo) > 120 else conteudo
        else:
            resumo = re.sub('<.*?>', '', resumo)
            resumo = resumo.replace('&nbsp;', ' ').replace('&#8217;', "'")
        
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
        return "🚨 Últimas Notícias do Litoral Norte!\n\n@bocanotrombonelitoral\n\n📲 Leia mais no link da bio!\n\n#Noticias #LitoralNorte"

def get_image_url_from_wordpress(image_id):
    """Busca a URL da imagem no WordPress"""
    try:
        logger.info(f"📡 Buscando imagem {image_id} no WordPress...")
        response = requests.get(f"{WORDPRESS_URL}{image_id}", timeout=15)
        
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

def criar_video_rapido(image_url):
    """Usa serviço externo para criar vídeo rapidamente"""
    try:
        logger.info("⚡ Criando vídeo via serviço externo...")
        
        # Usa o Cloudinary para criar vídeo rápido (converte imagem em vídeo)
        if 'cloudinary' not in image_url:
            # Se não for Cloudinary, converte a URL
            video_url = image_url.replace('/upload/', '/upload/f_mp4,du_15/')
            logger.info(f"✅ Vídeo externo criado: {video_url}")
            return video_url
        else:
            return image_url
            
    except Exception as e:
        logger.error(f"❌ Erro ao criar vídeo externo: {str(e)}")
        return None

def publicar_reels_facebook(video_url, caption):
    """Publica REELS no Facebook usando URL direta"""
    try:
        logger.info("📤 Publicando REELS no Facebook...")
        
        if not PAGE_TOKEN_BOCA:
            logger.error("❌ Token do Facebook não configurado")
            return False
        
        params = {
            'access_token': PAGE_TOKEN_BOCA,
            'description': caption,
            'file_url': video_url,
            'title': 'BOCA NO TROMBONE - Últimas Notícias'
        }
        
        response = requests.post(
            f'https://graph.facebook.com/v23.0/{FACEBOOK_PAGE_ID}/videos',
            params=params,
            timeout=60
        )
        
        if response.status_code == 200:
            logger.info("🎉 ✅ REELS PUBLICADO NO FACEBOOK!")
            return True
        else:
            logger.error(f"❌ Erro Facebook: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro na publicação Facebook: {str(e)}")
        return False

def publicar_reels_instagram(video_url, caption):
    """Publica REELS no Instagram usando URL direta"""
    try:
        logger.info("📤 Publicando REELS no Instagram...")
        
        if not PAGE_TOKEN_BOCA:
            logger.error("❌ Token do Instagram não configurado")
            return False
        
        create_params = {
            'access_token': PAGE_TOKEN_BOCA,
            'caption': caption,
            'media_type': 'REELS',
            'video_url': video_url
        }
        
        create_response = requests.post(
            f'https://graph.facebook.com/v23.0/{INSTAGRAM_ACCOUNT_ID}/media',
            params=create_params,
            timeout=60
        )
        
        if create_response.status_code != 200:
            logger.error(f"❌ Erro ao criar Reels: {create_response.text}")
            return False
        
        creation_id = create_response.json().get('id')
        if not creation_id:
            logger.error("❌ Não foi possível obter ID de criação")
            return False
        
        logger.info(f"✅ Reels criado: {creation_id}")
        
        # Aguarda 20 segundos para processamento
        import time
        time.sleep(20)
        
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
            logger.info("🎉 ✅ REELS PUBLICADO NO INSTAGRAM!")
            return True
        else:
            logger.error(f"❌ Erro publicação Instagram: {publish_response.text}")
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
        
        # Cria vídeo RÁPIDO usando serviço externo
        video_url = criar_video_rapido(image_url)
        
        if not video_url:
            logger.error("❌ Falha ao criar vídeo")
            return "❌ Erro ao criar vídeo", 500
        
        def publicar_tudo():
            facebook_ok = publicar_reels_facebook(video_url, caption)
            instagram_ok = publicar_reels_instagram(video_url, caption)
            
            if facebook_ok and instagram_ok:
                logger.info("🎉 ✅ REELS PUBLICADOS EM AMBAS AS PLATAFORMAS!")
            else:
                logger.warning("⚠️ Publicação em uma das plataformas falhou")
        
        thread = threading.Thread(target=publicar_tudo)
        thread.start()
        
        return "✅ Recebido! Publicação de REELS em andamento...", 200
        
    except Exception as e:
        logger.error(f"❌ Erro no webhook: {str(e)}")
        return "Erro interno", 500

@app.route('/')
def home():
    return "🚀 Sistema Funcionando! Boca no Trombone - Publicador de REELS", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"✅ Servidor pronto na porta {port}!")
    app.run(host='0.0.0.0', port=port)
