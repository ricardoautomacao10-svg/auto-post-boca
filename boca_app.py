from flask import Flask, request
import requests
import os
import threading
import logging
import json
import tempfile
from moviepy.editor import ImageClip, TextClip, CompositeVideoClip, ColorClip

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configurações - NOMES MANTIDOS COMO VOCÊ QUER!
PAGE_TOKEN_BOCA = os.getenv('PAGE_TOKEN_BOCA')
INSTAGRAM_ACCOUNT_ID = '17841464327364824'
FACEBOOK_PAGE_ID = '213776928485804'
WORDPRESS_URL = "https://jornalvozdolitoral.com/wp-json/wp/v2/media/"

def criar_legenda_completa(data):
    """Monta a legenda no formato profissional para Reels."""
    try:
        post_data = data.get('post', {})
        post_meta = data.get('post_meta', {})
        
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

def gerar_video_reels(image_url, titulo):
    """Gera vídeo vertical 9:16 (1080x1920) para Reels"""
    try:
        logger.info("🎬 Gerando vídeo Reels profissional...")
        
        response = requests.get(image_url, timeout=30)
        if response.status_code != 200:
            raise Exception("Erro ao baixar imagem")
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_img:
            tmp_img.write(response.content)
            image_path = tmp_img.name
        
        duration = 10
        width, height = 1080, 1920
        
        image_clip = ImageClip(image_path).resize(height=1600)
        image_clip = image_clip.set_position(('center', 'center'))
        image_clip = image_clip.set_duration(duration)
        
        background = ColorClip(size=(width, height), color=[0, 0, 0], duration=duration)
        
        overlay = ColorClip(size=(width, height), color=[0, 0, 0], duration=duration)
        overlay = overlay.set_opacity(0.3)
        
        red_box = ColorClip(size=(width, 100), color=[220, 0, 0], duration=duration)
        red_box = red_box.set_position(('center', 200))
        red_box = red_box.set_opacity(0.9)
        
        categoria_text = TextClip("BOCA NO TROMBONE", fontsize=40, color='white', font='Impact')
        categoria_text = categoria_text.set_position(('center', 215))
        categoria_text = categoria_text.set_duration(duration)
        
        white_box = ColorClip(size=(900, 300), color=[255, 255, 255], duration=duration)
        white_box = white_box.set_position(('center', 900))
        white_box = white_box.set_opacity(0.9)
        
        title_text = TextClip(titulo.upper(), fontsize=50, color='black', font='Impact', 
                             size=(800, 250), method='caption', align='center')
        title_text = title_text.set_position(('center', 920))
        title_text = title_text.set_duration(duration)
        
        logo_text = TextClip("BOCA NO TROMBONE", fontsize=50, color='white', font='Impact')
        logo_text = logo_text.set_position(('center', 100))
        logo_text = logo_text.set_duration(duration)
        
        video = CompositeVideoClip([
            background,
            image_clip,
            overlay,
            red_box,
            categoria_text,
            white_box,
            title_text,
            logo_text
        ], size=(width, height))
        
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_video:
            video_path = tmp_video.name
            video.write_videofile(video_path, fps=24, codec='libx264', audio=False, verbose=False, logger=None)
        
        os.unlink(image_path)
        logger.info("✅ Vídeo gerado com sucesso!")
        return video_path
        
    except Exception as e:
        logger.error(f"❌ Erro ao gerar vídeo: {str(e)}")
        return None

def publicar_facebook(video_path, caption):
    """Publica vídeo no Facebook"""
    try:
        logger.info("📤 Publicando no Facebook...")
        
        if not PAGE_TOKEN_BOCA:
            logger.error("❌ Token não configurado")
            return False
            
        files = {'source': open(video_path, 'rb')}
        params = {
            'access_token': PAGE_TOKEN_BOCA,
            'description': caption,
            'title': 'BOCA NO TROMBONE - Últimas Notícias'
        }
        
        response = requests.post(
            f'https://graph.facebook.com/v23.0/{FACEBOOK_PAGE_ID}/videos',
            params=params,
            files=files,
            timeout=120
        )
        
        if response.status_code == 200:
            logger.info("🎉 ✅ VÍDEO PUBLICADO NO FACEBOOK!")
            return True
        else:
            logger.error(f"❌ Erro Facebook: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro na publicação Facebook: {str(e)}")
        return False

def publicar_instagram(video_path, caption):
    """Publica vídeo no Instagram Reels"""
    try:
        logger.info("📤 Publicando no Instagram...")
        
        if not PAGE_TOKEN_BOCA:
            logger.error("❌ Token não configurado")
            return False
        
        files = {'video': open(video_path, 'rb')}
        create_params = {
            'access_token': PAGE_TOKEN_BOCA,
            'caption': caption,
            'media_type': 'REELS'
        }
        
        create_response = requests.post(
            f'https://graph.facebook.com/v23.0/{INSTAGRAM_ACCOUNT_ID}/media',
            params=create_params,
            files=files,
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
        
        publish_params = {
            'access_token': PAGE_TOKEN_BOCA,
            'creation_id': creation_id
        }
        
        import time
        time.sleep(10)
        
        publish_response = requests.post(
            f'https://graph.facebook.com/v23.0/{INSTAGRAM_ACCOUNT_ID}/media_publish',
            params=publish_params,
            timeout=120
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
        
        video_path = gerar_video_reels(image_url, data.get('post', {}).get('post_title', ''))
        
        if not video_path:
            logger.error("❌ Falha ao gerar vídeo")
            return "❌ Erro ao gerar vídeo", 500
        
        def publicar_tudo():
            facebook_ok = publicar_facebook(video_path, caption)
            instagram_ok = publicar_instagram(video_path, caption)
            
            os.unlink(video_path)
            
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
