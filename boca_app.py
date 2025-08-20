import os
import time
import requests
from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from base64 import b64encode
import cloudinary
import cloudinary.uploader
import tempfile
from moviepy.editor import ImageClip

# Carrega variáveis de ambiente
load_dotenv()
app = Flask(__name__)

# Config WordPress
WP_URL = os.getenv('WP_URL')
WP_USER = os.getenv('WP_USER')
WP_PASSWORD = os.getenv('WP_PASSWORD')
HEADERS_WP = {}
if all([WP_URL, WP_USER, WP_PASSWORD]):
    credentials = f"{WP_USER}:{WP_PASSWORD}"
    token_wp = b64encode(credentials.encode())
    HEADERS_WP = {'Authorization': f'Basic {token_wp.decode("utf-8")}'}

# Config Meta
INSTAGRAM_ID = os.getenv('BOCA_INSTAGRAM_ID')
FACEBOOK_PAGE_ID = os.getenv('BOCA_FACEBOOK_PAGE_ID')
META_API_TOKEN = os.getenv('BOCA_META_API_TOKEN')
GRAPH_API_VERSION = 'v21.0'

# Config Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

# Config vídeo
VIDEO_DURATION = 10
VIDEO_FPS = 24

def fazer_upload_cloudinary(arquivo_path):
    """Faz upload para Cloudinary e retorna URL"""
    try:
        print("☁️ Fazendo upload para Cloudinary...")
        resultado = cloudinary.uploader.upload(
            arquivo_path,
            resource_type="video",
            folder="boca_reels",
            timeout=300  # 5 minutos para uploads grandes
        )
        return resultado['secure_url']
    except Exception as e:
        print(f"❌ Erro no upload: {e}")
        return None

def gerar_video(url_imagem):
    """Gera vídeo a partir de imagem"""
    try:
        print("📥 Baixando imagem...")
        resposta = requests.get(url_imagem, timeout=30)
        resposta.raise_for_status()
        
        # Criar arquivos temporários
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as img_temp:
            img_path = img_temp.name
            img_temp.write(resposta.content)
        
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as video_temp:
            video_path = video_temp.name
        
        print("🎬 Criando vídeo...")
        clip = ImageClip(img_path, duration=VIDEO_DURATION)
        clip = clip.set_fps(VIDEO_FPS)
        clip.write_videofile(
            video_path, 
            codec="libx264", 
            audio=False, 
            verbose=False,
            logger=None,
            threads=4  # Otimização para Render
        )
        
        # Limpar imagem temporária
        os.unlink(img_path)
        
        return video_path
        
    except Exception as e:
        print(f"❌ Erro ao gerar vídeo: {e}")
        # Limpeza em caso de erro
        if 'img_path' in locals() and os.path.exists(img_path):
            os.unlink(img_path)
        if 'video_path' in locals() and os.path.exists(video_path):
            os.unlink(video_path)
        return None

def publicar_instagram(url_video, legenda):
    """Publica no Instagram"""
    try:
        print("📤 Publicando no Instagram...")
        url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{INSTAGRAM_ID}/media"
        
        params = {
            "media_type": "REELS",
            "video_url": url_video,
            "caption": legenda[:2200],
            "access_token": META_API_TOKEN
        }
        
        resposta = requests.post(url, data=params, timeout=60)
        resposta.raise_for_status()
        return True
        
    except Exception as e:
        print(f"❌ Erro Instagram: {e}")
        return False

def publicar_facebook(url_video, legenda):
    """Publica no Facebook"""
    try:
        print("📤 Publicando no Facebook...")
        url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{FACEBOOK_PAGE_ID}/videos"
        
        params = {
            "file_url": url_video,
            "description": legenda,
            "access_token": META_API_TOKEN
        }
        
        resposta = requests.post(url, data=params, timeout=60)
        resposta.raise_for_status()
        return True
        
    except Exception as e:
        print(f"❌ Erro Facebook: {e}")
        return False

@app.route('/webhook-boca', methods=['POST'])
def webhook_receiver():
    print("🔔 Webhook recebido")
    
    video_path = None
    try:
        dados = request.json
        post_id = dados.get("post_id")
        
        if not post_id:
            return jsonify({"erro": "Post ID não fornecido"}), 400
        
        # Buscar dados do post
        url_post = f"{WP_URL}/wp-json/wp/v2/posts/{post_id}"
        resposta = requests.get(url_post, headers=HEADERS_WP, timeout=30)
        resposta.raise_for_status()
        post = resposta.json()
        
        # Extrair título e resumo
        titulo = BeautifulSoup(post.get('title', {}).get('rendered', ''), 'html.parser').get_text()
        resumo = BeautifulSoup(post.get('excerpt', {}).get('rendered', ''), 'html.parser').get_text(strip=True)
        
        # Buscar imagem
        imagem_id = post.get('featured_media')
        if not imagem_id:
            return jsonify({"erro": "Sem imagem"}), 400
        
        url_imagem = f"{WP_URL}/wp-json/wp/v2/media/{imagem_id}"
        resposta_imagem = requests.get(url_imagem, headers=HEADERS_WP, timeout=30)
        resposta_imagem.raise_for_status()
        url_imagem = resposta_imagem.json().get("source_url")
        
        # Gerar vídeo
        video_path = gerar_video(url_imagem)
        if not video_path:
            return jsonify({"erro": "Falha ao gerar vídeo"}), 500
        
        # Fazer upload
        url_publica = fazer_upload_cloudinary(video_path)
        if not url_publica:
            return jsonify({"erro": "Falha no upload"}), 500
        
        # Criar legenda
        legenda = f"{titulo}\n\n{resumo}\n\n📖 Leia a matéria completa no site! #BocaNoTrombone"
        
        # Publicar
        instagram_ok = publicar_instagram(url_publica, legenda)
        facebook_ok = publicar_facebook(url_publica, legenda)
        
        if instagram_ok or facebook_ok:
            return jsonify({"sucesso": True}), 200
        else:
            return jsonify({"erro": "Falha na publicação"}), 500
            
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        return jsonify({"erro": str(e)}), 500
        
    finally:
        # Limpeza
        if video_path and os.path.exists(video_path):
            try:
                os.unlink(video_path)
            except:
                pass

@app.route('/')
def home():
    return "🚀 Boca no Trombone API rodando!"

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
