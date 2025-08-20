import os
import io
import time
import requests
from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from base64 import b64encode
from moviepy.editor import ImageClip, AudioFileClip

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

# Config vídeo
VIDEO_DURATION = 10  # segundos
VIDEO_FPS = 24
VIDEO_FILENAME = "temp_video.mp4"

# ========================= FUNÇÕES =========================

def gerar_video_da_imagem(url_imagem, arquivo_saida=VIDEO_FILENAME, duracao=VIDEO_DURATION):
    """Gera vídeo MP4 a partir de uma imagem"""
    try:
        print("🎬 Baixando imagem para vídeo...")
        r = requests.get(url_imagem, stream=True, timeout=15)
        r.raise_for_status()
        with open("temp_img.jpg", "wb") as f:
            f.write(r.content)
        
        print("🎬 Criando vídeo com moviepy...")
        clip = ImageClip("temp_img.jpg", duration=duracao)
        clip = clip.set_fps(VIDEO_FPS)
        clip.write_videofile(arquivo_saida, codec="libx264", audio=False)
        print("✅ Vídeo gerado com sucesso!")
        return arquivo_saida
    except Exception as e:
        print(f"❌ Erro ao gerar vídeo: {e}")
        return None

def publicar_reel_instagram(arquivo_video, legenda):
    """Publica vídeo no Instagram Reels"""
    try:
        print("📤 Criando container de vídeo no Instagram...")
        url_container = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{INSTAGRAM_ID}/media"
        params = {
            "media_type": "VIDEO",
            "video_url": arquivo_video,  # URL público ou caminho? Preferível URL pública
            "caption": legenda,
            "access_token": META_API_TOKEN
        }
        r = requests.post(url_container, data=params)
        r.raise_for_status()
        creation_id = r.json()["id"]
        print(f"✅ Container criado: {creation_id}")

        # Checar status do container
        status = "IN_PROGRESS"
        tentativas = 0
        while status != "FINISHED" and tentativas < 30:
            time.sleep(5)
            check_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{creation_id}?fields=status_code&access_token={META_API_TOKEN}"
            status_resp = requests.get(check_url).json()
            status = status_resp.get("status_code", "ERROR")
            print(f"⏳ Status do vídeo: {status}")
            if status == "ERROR":
                print("❌ Erro no processamento do vídeo:", status_resp)
                return False
            tentativas += 1

        if status != "FINISHED":
            print("⚠️ Timeout atingido sem finalizar processamento do vídeo.")
            return False

        # Publica o vídeo
        publish_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{INSTAGRAM_ID}/media_publish"
        r_publish = requests.post(publish_url, data={
            "creation_id": creation_id,
            "access_token": META_API_TOKEN
        })
        r_publish.raise_for_status()
        print("🎉 Reel publicado no Instagram:", r_publish.json())
        return True
    except Exception as e:
        print("❌ Erro publicar_reel_instagram:", str(e))
        return False

def publicar_video_facebook(arquivo_video, legenda):
    """Publica vídeo na página do Facebook"""
    try:
        print("📤 Publicando vídeo no Facebook...")
        url_fb = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{FACEBOOK_PAGE_ID}/videos"
        params = {
            "file_url": arquivo_video,  # precisa ser URL pública
            "description": legenda,
            "access_token": META_API_TOKEN
        }
        r = requests.post(url_fb, data=params)
        r.raise_for_status()
        print("🎉 Vídeo publicado no Facebook:", r.json())
        return True
    except Exception as e:
        print("❌ Erro publicar_video_facebook:", str(e))
        return False

# ========================= WEBHOOK =========================

@app.route('/webhook-boca', methods=['POST'])
def webhook_receiver():
    print("\n🔔 Webhook recebido (Boca no Trombone)")
    try:
        dados = request.json
        post_id = dados.get("post_id")
        if not post_id:
            raise ValueError("Webhook não enviou 'post_id'.")

        print(f"📝 Processando post ID: {post_id}")
        url_api_post = f"{WP_URL}/wp-json/wp/v2/posts/{post_id}"
        r_post = requests.get(url_api_post, headers=HEADERS_WP, timeout=15)
        r_post.raise_for_status()
        post_data = r_post.json()

        titulo = BeautifulSoup(post_data.get('title', {}).get('rendered', ''), 'html.parser').get_text()
        resumo = BeautifulSoup(post_data.get('excerpt', {}).get('rendered', ''), 'html.parser').get_text(strip=True)
        id_imagem = post_data.get('featured_media')
        if not id_imagem:
            print("⚠️ Post sem imagem de destaque, ignorando.")
            return jsonify({"status": "ignorado_sem_imagem"}), 200

        # Busca URL da imagem
        url_api_media = f"{WP_URL}/wp-json/wp/v2/media/{id_imagem}"
        r_media = requests.get(url_api_media, headers=HEADERS_WP, timeout=15)
        r_media.raise_for_status()
        url_imagem = r_media.json().get("source_url")

        # Gera vídeo
        arquivo_video = gerar_video_da_imagem(url_imagem)
        if not arquivo_video:
            return jsonify({"status": "erro_gerar_video"}), 500

        legenda_final = f"{titulo}\n\n{resumo}\n\nLeia a matéria completa no site. #BocaNoTrombone #Reels #Noticias"

        sucesso_ig = publicar_reel_instagram(arquivo_video, legenda_final)
        sucesso_fb = publicar_video_facebook(arquivo_video, legenda_final)

        if sucesso_ig or sucesso_fb:
            print("🎉 Publicação concluída!")
            return jsonify({"status": "sucesso"}), 200
        else:
            print("❌ Nenhuma publicação foi bem-sucedida.")
            return jsonify({"status": "erro_publicacao"}), 500

    except Exception as e:
        print("❌ Erro ao processar webhook:", str(e))
        return jsonify({"status": "erro_processamento"}), 500

# ========================= HEALTH CHECK =========================

@app.route('/')
def health_check():
    return "Serviço BOCA NO TROMBONE rodando.", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
