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
from moviepy.editor import ImageClip, CompositeVideoClip
from moviepy.video.fx.all import resize
from PIL import Image, ImageDraw, ImageFont
import numpy as np

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

# Configurações de design
VIDEO_DURATION = 10
VIDEO_FPS = 24
VIDEO_SIZE = (1080, 1920)

# ========================= FUNÇÕES SIMPLIFICADAS =========================

def carregar_fontes_locais():
    """Carrega apenas fontes locais - SEM downloads"""
    fontes = {}
    try:
        # Verifica se as fontes existem na raiz
        fontes_disponiveis = {
            "TITULO": "Anton-Regular.ttf",
            "TEXTO": "Roboto-Bold.ttf", 
            "RODAPE": "Roboto-Black.ttf"
        }
        
        for nome, arquivo in fontes_disponiveis.items():
            caminho = os.path.join(os.path.dirname(__file__), arquivo)
            if os.path.exists(caminho):
                # Cria cópia temporária
                with open(caminho, 'rb') as f_origem:
                    with tempfile.NamedTemporaryFile(suffix='.ttf', delete=False) as f_temp:
                        f_temp.write(f_origem.read())
                        fontes[nome] = f_temp.name
                print(f"✅ Fonte {nome} carregada localmente")
            else:
                print(f"⚠️ Fonte {arquivo} não encontrada, usando padrão")
                fontes[nome] = None
        
        return fontes
        
    except Exception as e:
        print(f"❌ Erro ao carregar fontes: {e}")
        return None

def aplicar_pan_zoom(clip_imagem):
    """Aplica efeito de pan e zoom - VERSÃO SIMPLIFICADA E CORRIGIDA"""
    try:
        # Aumenta um pouco a imagem para efeito de zoom
        clip_ampliado = clip_imagem.resize(1.1)
        
        # Movimento simples de pan
        def movimento(t):
            progresso = t / VIDEO_DURATION
            x = 'center'  # Mantém centralizado horizontalmente
            y = 50 * progresso  # Movimento vertical suave
            return (x, y)
        
        return clip_ampliado.set_position(movimento)
        
    except Exception as e:
        print(f"❌ Erro no pan/zoom (usando fallback): {e}")
        # Fallback: retorna a imagem original centralizada
        return clip_imagem.set_position(('center', 'center'))
        
def criar_overlay_boca(titulo, resumo, caminho_fontes):
    """Cria overlay simplificado"""
    try:
        overlay = Image.new('RGBA', VIDEO_SIZE, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Configurações de fonte com fallback
        try:
            if caminho_fontes.get("TEXTO"):
                fonte_texto = ImageFont.truetype(caminho_fontes["TEXTO"], 45)
            else:
                fonte_texto = ImageFont.load_default()
        except:
            fonte_texto = ImageFont.load_default()
        
        # Cores
        cor_texto = (0, 0, 0)
        cor_fundo = (255, 255, 255, 200)
        cor_destaque = (255, 0, 0)
        
        # Fundo para texto
        draw.rectangle([(50, VIDEO_SIZE[1]//2 - 100), 
                       (VIDEO_SIZE[0]-50, VIDEO_SIZE[1] - 150)], 
                      fill=cor_fundo)
        
        # Borda vermelha
        draw.rectangle([(45, VIDEO_SIZE[1]//2 - 105), 
                       (VIDEO_SIZE[0]-45, VIDEO_SIZE[1] - 145)], 
                      outline=cor_destaque, width=5)

        # Título (simplificado)
        titulo = titulo.upper()[:50]  # Limita caracteres
        y_pos = VIDEO_SIZE[1]//2 - 50
        x_pos = (VIDEO_SIZE[0] - 1000) // 2  # Posição aproximada
        
        draw.text((x_pos, y_pos), titulo, font=fonte_texto, fill=cor_texto)
        
        # Rodapé
        rodape = "@BOCANOTROMBONELITORAL"
        y_pos = VIDEO_SIZE[1] - 120
        x_pos = (VIDEO_SIZE[0] - 600) // 2
        
        draw.rectangle([(x_pos-20, y_pos-10), (x_pos+600, y_pos+50)], fill=cor_texto)
        draw.text((x_pos, y_pos), rodape, font=fonte_texto, fill=(255, 255, 255))
        
        # Salvar overlay
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as overlay_temp:
            overlay_path = overlay_temp.name
            overlay.save(overlay_path, 'PNG')
        
        return overlay_path
        
    except Exception as e:
        print(f"❌ Erro ao criar overlay: {e}")
        return None

def gerar_video_estilo_boca(url_imagem, titulo, resumo):
    """Gera vídeo simplificado"""
    fontes = None
    overlay_path = None
    video_path = None
    img_path = None
    
    try:
        # Carrega fontes locais
        fontes = carregar_fontes_locais()
        
        # Baixa imagem
        resposta = requests.get(url_imagem, timeout=30)
        resposta.raise_for_status()
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as img_temp:
            img_path = img_temp.name
            img_temp.write(resposta.content)
        
        # Cria overlay
        overlay_path = criar_overlay_boca(titulo, resumo, fontes or {})
        
        # Cria vídeo
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as video_temp:
            video_path = video_temp.name
        
        # Clip da imagem
        clip_imagem = ImageClip(img_path, duration=VIDEO_DURATION)
        clip_imagem = aplicar_pan_zoom(clip_imagem)
        clip_imagem = clip_imagem.resize(width=VIDEO_SIZE[0])
        
        # Clip do overlay (se existir)
        if overlay_path and os.path.exists(overlay_path):
            clip_overlay = ImageClip(overlay_path, duration=VIDEO_DURATION)
            clip_overlay = clip_overlay.set_position(('center', 'center'))
            video_final = CompositeVideoClip([clip_imagem, clip_overlay])
        else:
            video_final = clip_imagem
        
        video_final = video_final.set_fps(VIDEO_FPS)
        video_final.write_videofile(video_path, codec="libx264", audio=False, verbose=False, logger=None)
        
        return video_path
        
    except Exception as e:
        print(f"❌ Erro ao gerar vídeo: {e}")
        return None
        
    finally:
        # Limpeza
        for path in [overlay_path, img_path]:
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except:
                    pass
        if fontes:
            for font_path in fontes.values():
                if font_path and os.path.exists(font_path):
                    try:
                        os.unlink(font_path)
                    except:
                        pass

def fazer_upload_cloudinary(arquivo_path):
    """Upload para Cloudinary"""
    try:
        resultado = cloudinary.uploader.upload(arquivo_path, resource_type="video", folder="boca_reels")
        return resultado['secure_url']
    except Exception as e:
        print(f"❌ Erro no upload: {e}")
        return None

def publicar_rede_social(url_video, legenda, plataforma):
    """Publica nas redes sociais"""
    try:
        if plataforma == "instagram":
            url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{INSTAGRAM_ID}/media"
            params = {"media_type": "REELS", "video_url": url_video, "caption": legenda[:2200], "access_token": META_API_TOKEN}
        else:
            url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{FACEBOOK_PAGE_ID}/videos"
            params = {"file_url": url_video, "description": legenda, "access_token": META_API_TOKEN}
        
        resposta = requests.post(url, data=params, timeout=60)
        resposta.raise_for_status()
        return True
        
    except Exception as e:
        print(f"❌ Erro ao publicar: {e}")
        return False

# ========================= WEBHOOK =========================

@app.route('/webhook-boca', methods=['POST'])
def webhook_receiver():
    print("🔔 Webhook recebido")
    
    video_path = None
    try:
        dados = request.json
        post_id = dados.get("post_id")
        
        if not post_id:
            return jsonify({"erro": "Sem post_id"}), 400
        
        # Busca dados do post
        url_post = f"{WP_URL}/wp-json/wp/v2/posts/{post_id}"
        resposta = requests.get(url_post, headers=HEADERS_WP, timeout=30)
        resposta.raise_for_status()
        post = resposta.json()
        
        # Extrai dados
        titulo = BeautifulSoup(post.get('title', {}).get('rendered', ''), 'html.parser').get_text()
        resumo = BeautifulSoup(post.get('excerpt', {}).get('rendered', ''), 'html.parser').get_text(strip=True)
        
        # Busca imagem
        imagem_id = post.get('featured_media')
        if not imagem_id:
            return jsonify({"erro": "Sem imagem"}), 400
        
        url_imagem = f"{WP_URL}/wp-json/wp/v2/media/{imagem_id}"
        resposta_imagem = requests.get(url_imagem, headers=HEADERS_WP, timeout=30)
        resposta_imagem.raise_for_status()
        url_imagem = resposta_imagem.json().get("source_url")
        
        # Gera vídeo
        video_path = gerar_video_estilo_boca(url_imagem, titulo, resumo)
        if not video_path:
            return jsonify({"erro": "Falha ao gerar vídeo"}), 500
        
        # Upload
        url_publica = fazer_upload_cloudinary(video_path)
        if not url_publica:
            return jsonify({"erro": "Falha no upload"}), 500
        
        # Publica
        legenda = f"{titulo}\n\n{resumo}\n\n📖 Leia mais!\n\n#BocaNoTrombone #LitoralNorte"
        instagram_ok = publicar_rede_social(url_publica, legenda, "instagram")
        facebook_ok = publicar_rede_social(url_publica, legenda, "facebook")
        
        if instagram_ok or facebook_ok:
            return jsonify({"sucesso": True}), 200
        else:
            return jsonify({"erro": "Falha na publicação"}), 500
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        return jsonify({"erro": str(e)}), 500
        
    finally:
        if video_path and os.path.exists(video_path):
            try:
                os.unlink(video_path)
            except:
                pass

@app.route('/')
def home():
    return "🚀 BOCA NO TROMBONE - Sistema de Automação"

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
