from flask import Flask, request
import requests
import os
import threading
import logging
import tempfile
import re
from moviepy.editor import ImageClip, TextClip, CompositeVideoClip, ColorClip

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configurações
PAGE_TOKEN_BOCA = os.getenv('PAGE_TOKEN_BOCA')
INSTAGRAM_ACCOUNT_ID = '17841464327364824'
FACEBOOK_PAGE_ID = '213776928485804'
WORDPRESS_URL = "https://jornalvozdolitoral.com/wp-json/wp/v2/media/"

# Caminhos das fontes (QUE VOCÊ JÁ TEM!)
FONT_ANTON = "Anton-Regular.tif"
FONT_ROBOTO_BOLD = "Roboto-Bold.tif"
FONT_ROBOTO_BLACK = "Roboto-Black.tif"

def criar_legenda_completa(data):
    """Monta a legenda profissional para Reels - SEM HTML."""
    try:
        post_data = data.get('post', {})
        
        # Pega o título e LIMPA HTML
        titulo = post_data.get('post_title', '')
        titulo = re.sub('<.*?>', '', titulo)  # Remove todas as tags HTML
        
        # Pega o resumo e LIMPA HTML
        resumo = post_data.get('post_excerpt', '')
        if not resumo:
            conteudo = post_data.get('post_content', '')
            conteudo = re.sub('<.*?>', '', conteudo)  # Remove HTML
            resumo = conteudo[:150] + "..." if len(conteudo) > 150 else conteudo
        else:
            resumo = re.sub('<.*?>', '', resumo)  # Remove HTML do resumo
        
        # Legenda formatada CORRETAMENTE
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
        titulo = data.get('post', {}).get('post_title', '')
        return f"{titulo}\n\nLeia a matéria completa no site! 📖"

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

def criar_video_profissional(image_url, titulo):
    """Cria vídeo PROFISSIONAL com as fontes do Boca no Trombone"""
    try:
        logger.info("🎬 Criando vídeo profissional com fontes personalizadas...")
        
        # Download da imagem
        response = requests.get(image_url, timeout=30)
        if response.status_code != 200:
            raise Exception("Erro ao baixar imagem")
        
        # Salva imagem temporária
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_img:
            tmp_img.write(response.content)
            image_path = tmp_img.name
        
        # Configurações do vídeo REELS (1080x1920)
        duration = 10
        width, height = 1080, 1920
        
        # Imagem de fundo (centralizada com zoom)
        image_clip = ImageClip(image_path)
        image_clip = image_clip.resize(height=height)
        image_clip = image_clip.crop(x_center=image_clip.w/2, y_center=image_clip.h/2, width=width, height=height)
        image_clip = image_clip.set_duration(duration)
        
        # Overlay escuro para contraste
        overlay = ColorClip(size=(width, height), color=[0, 0, 0], duration=duration)
        overlay = overlay.set_opacity(0.4)
        
        # LOGO BOCA NO TROMBONE (topo)
        logo_text = TextClip("BOCA NO TROMBONE", fontsize=60, color='white', font=FONT_ANTON)
        logo_text = logo_text.set_position(('center', 80))
        logo_text = logo_text.set_duration(duration)
        
        # BARRA VERMELHA (categoria)
        red_bar = ColorClip(size=(width, 80), color=[220, 0, 0], duration=duration)
        red_bar = red_bar.set_position(('center', 180))
        red_bar = red_bar.set_opacity(0.9)
        
        categoria_text = TextClip("ÚLTIMAS NOTÍCIAS", fontsize=40, color='white', font=FONT_ROBOTO_BOLD)
        categoria_text = categoria_text.set_position(('center', 200))
        categoria_text = categoria_text.set_duration(duration)
        
        # CAIXA BRANCA com TÍTULO
        white_box = ColorClip(size=(1000, 300), color=[255, 255, 255], duration=duration)
        white_box = white_box.set_position(('center', 900))
        white_box = white_box.set_opacity(0.9)
        
        # Título formatado (usando a fonte Anton)
        title_text = TextClip(titulo.upper(), fontsize=48, color='black', font=FONT_ANTON,
                             size=(900, 250), method='caption', align='center', stroke_color='black', stroke_width=1)
        title_text = title_text.set_position(('center', 920))
        title_text = title_text.set_duration(duration)
        
        # CREDITOS (rodapé)
        creditos_text = TextClip("@bocanotrombonelitoral", fontsize=30, color='white', font=FONT_ROBOTO_BLACK)
        creditos_text = creditos_text.set_position(('center', 1850))
        creditos_text = creditos_text.set_duration(duration)
        
        # Compõe todos os elementos
        video = CompositeVideoClip([
            image_clip,
            overlay,
            red_bar,
            categoria_text,
            white_box,
            title_text,
            logo_text,
            creditos_text
        ], size=(width, height))
        
        # Salva vídeo temporário
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_video:
            video_path = tmp_video.name
            video.write_videofile(video_path, fps=24, codec='libx264', audio=False, 
                                verbose=False, logger=None, threads=4)
        
        os.unlink(image_path)
        logger.info("✅ Vídeo profissional criado com sucesso!")
        return video_path
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar vídeo profissional: {str(e)}")
        return None

def publicar_facebook_reels(video_path, caption):
    """Publica REELS no Facebook"""
    try:
        logger.info("📤 Publicando REELS no Facebook...")
        
        if not PAGE_TOKEN_BOCA:
            logger.error("❌ Token do Facebook não configurado")
            return False
        
        with open(video_path, 'rb') as video_file:
            files = {'source': video_file}
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
            logger.info("🎉 ✅ REELS PUBLICADO NO FACEBOOK!")
            return True
        else:
            logger.error(f"❌ Erro Facebook: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro na publicação Facebook: {str(e)}")
        return False

def publicar_instagram_reels(video_path, caption):
    """Publica REELS no Instagram"""
    try:
        logger.info("📤 Publicando REELS no Instagram...")
        
        if not PAGE_TOKEN_BOCA:
            logger.error("❌ Token do Instagram não configurado")
            return False
        
        with open(video_path, 'rb') as video_file:
            files = {'video': video_file}
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
            logger.error(f"❌ Erro ao criar Reels: {create_response.text}")
            return False
        
        creation_id = create_response.json().get('id')
        if not creation_id:
            logger.error("❌ Não foi possível obter ID de criação")
            return False
        
        logger.info(f"✅ Reels criado: {creation_id}")
        
        # Publicar
        publish_params = {
            'access_token': PAGE_TOKEN_BOCA,
            'creation_id': creation_id
        }
        
        import time
        time.sleep(5)
        
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
        
        # Cria vídeo PROFISSIONAL
        video_path = criar_video_profissional(image_url, data.get('post', {}).get('post_title', ''))
        
        if not video_path:
            logger.error("❌ Falha ao criar vídeo profissional")
            return "❌ Erro ao criar vídeo", 500
        
        def publicar_tudo():
            facebook_ok = publicar_facebook_reels(video_path, caption)
            instagram_ok = publicar_instagram_reels(video_path, caption)
            
            # Limpa arquivo temporário
            if os.path.exists(video_path):
                os.unlink(video_path)
            
            if facebook_ok and instagram_ok:
                logger.info("🎉 ✅ REELS PUBLICADO EM AMBAS AS PLATAFORMAS!")
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
