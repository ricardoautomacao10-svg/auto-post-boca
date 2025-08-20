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
from moviepy.editor import ImageClip, CompositeVideoClip, TextClip
from moviepy.video.fx.all import resize, crop
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

# Configurações de design - ESTILO BOCA NO TROMBONE
VIDEO_DURATION = 10  # 10 segundos para retenção
VIDEO_FPS = 24
VIDEO_SIZE = (1080, 1920)  # Formato Reels/Stories

# Configurações de tipografia (fontes fortes e populares) - URLs CORRIGIDAS
GOOGLE_FONTS = {
    "TITULO": "https://github.com/google/fonts/raw/main/ofl/anton/Anton-Regular.ttf",
    "TEXTO": "https://github.com/google/fonts/raw/main/ofl/roboto/Roboto-Bold.ttf",
    "RODAPE": "https://github.com/google/fonts/raw/main/ofl/roboto/Roboto-Black.ttf"
}

# ========================= FUNÇÕES DE DESIGN =========================

def baixar_fontes():
    """Baixa as fontes do Google Fonts"""
    fontes = {}
    try:
        for nome, url in GOOGLE_FONTS.items():
            resposta = requests.get(url, timeout=30)
            resposta.raise_for_status()
            
            with tempfile.NamedTemporaryFile(suffix='.ttf', delete=False) as font_temp:
                font_temp.write(resposta.content)
                fontes[nome] = font_temp.name
            
            print(f"✅ Fonte {nome} baixada")
        
        return fontes
        
    except Exception as e:
        print(f"❌ Erro ao baixar fontes: {e}")
        return None

def aplicar_pan_zoom(clip_imagem):
    """Aplica efeito de pan e zoom na imagem"""
    try:
        # Aumenta a imagem para permitir o zoom
        clip_ampliado = resize(clip_imagem, 1.2)
        
        # Define os keyframes para o movimento de pan
        def movimento(t):
            # Movimento suave de cima para baixo
            x = 0  # Centro horizontal
            y = 200 * (t / VIDEO_DURATION)  # Movimento vertical suave
            return ('center', y)
        
        # Aplica o movimento
        clip_com_movimento = clip_ampliado.set_position(movimento)
        return clip_com_movimento
        
    except Exception as e:
        print(f"❌ Erro no pan/zoom: {e}")
        return clip_imagem

def criar_overlay_boca(titulo, resumo, caminho_fontes):
    """Cria overlay no estilo Boca no Trombone - PRETO E BRANCO COM ENFASE"""
    try:
        # Criar imagem transparente para o overlay
        overlay = Image.new('RGBA', VIDEO_SIZE, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Carregar fontes (Anton para título - forte e impactante)
        fonte_titulo = ImageFont.truetype(caminho_fontes["TITULO"], 80)
        fonte_texto = ImageFont.truetype(caminho_fontes["TEXTO"], 45)
        fonte_rodape = ImageFont.truetype(caminho_fontes["RODAPE"], 40)
        
        # CORES DO BOCA NO TROMBONE
        cor_texto = (0, 0, 0)  # PRETO puro
        cor_fundo = (255, 255, 255, 200)  # BRANCO com transparência
        cor_destaque = (255, 0, 0)  # VERMELHO para destaques
        
        # Fundo semi-transparente para os textos (para melhor legibilidade)
        draw.rectangle([(50, VIDEO_SIZE[1]//2 - 100), 
                       (VIDEO_SIZE[0]-50, VIDEO_SIZE[1] - 150)], 
                      fill=cor_fundo)
        
        # Adicionar borda vermelha (estilo jornalístico)
        draw.rectangle([(45, VIDEO_SIZE[1]//2 - 105), 
                       (VIDEO_SIZE[0]-45, VIDEO_SIZE[1] - 145)], 
                      outline=cor_destaque, width=5)

        # Adicionar título em PRETO (todo maiúsculo para impacto)
        titulo = titulo.upper()
        lines = []
        words = titulo.split()
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=fonte_titulo)
            width = bbox[2] - bbox[0]
            
            if width < VIDEO_SIZE[0] - 150:
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        # Posicionar título (centralizado)
        y_pos = VIDEO_SIZE[1]//2 - 50
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=fonte_titulo)
            width = bbox[2] - bbox[0]
            x_pos = (VIDEO_SIZE[0] - width) // 2
            
            # Texto PRETO e impactante
            draw.text((x_pos, y_pos), line, font=fonte_titulo, fill=cor_texto)
            y_pos += bbox[3] - bbox[1] + 5
        
        # Adicionar resumo (se couber)
        if resumo and y_pos < VIDEO_SIZE[1] - 250:
            resumo = resumo.upper()
            resumo_lines = []
            words = resumo.split()
            current_line = []
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                bbox = draw.textbbox((0, 0), test_line, font=fonte_texto)
                width = bbox[2] - bbox[0]
                
                if width < VIDEO_SIZE[0] - 150:
                    current_line.append(word)
                else:
                    resumo_lines.append(' '.join(current_line))
                    current_line = [word]
            
            if current_line:
                resumo_lines.append(' '.join(current_line))
            
            # Limitar a 2 linhas
            resumo_lines = resumo_lines[:2]
            
            y_pos += 20
            for line in resumo_lines:
                bbox = draw.textbbox((0, 0), line, font=fonte_texto)
                width = bbox[2] - bbox[0]
                x_pos = (VIDEO_SIZE[0] - width) // 2
                
                draw.text((x_pos, y_pos), line, font=fonte_texto, fill=cor_texto)
                y_pos += bbox[3] - bbox[1] + 5
        
        # Adicionar rodapé com @BOCANOTROMBONELITORAL
        rodape = "@BOCANOTROMBONELITORAL"
        bbox = draw.textbbox((0, 0), rodape, font=fonte_rodape)
        width = bbox[2] - bbox[0]
        x_pos = (VIDEO_SIZE[0] - width) // 2
        y_pos = VIDEO_SIZE[1] - 120
        
        # Fundo para o rodapé
        draw.rectangle([(x_pos-20, y_pos-10), 
                       (x_pos+width+20, y_pos+bbox[3]-bbox[1]+10)], 
                      fill=cor_texto)  # Fundo PRETO
        
        # Texto do rodapé em BRANCO
        draw.text((x_pos, y_pos), rodape, font=fonte_rodape, fill=(255, 255, 255))
        
        # Salvar overlay temporário
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as overlay_temp:
            overlay_path = overlay_temp.name
            overlay.save(overlay_path, 'PNG')
        
        return overlay_path
        
    except Exception as e:
        print(f"❌ Erro ao criar overlay: {e}")
        return None

def gerar_video_estilo_boca(url_imagem, titulo, resumo):
    """Gera vídeo no estilo Boca no Trombone - 10 segundos com pan/zoom"""
    fontes = None
    overlay_path = None
    video_path = None
    img_path = None
    
    try:
        # Baixar fontes
        fontes = baixar_fontes()
        if not fontes:
            return None
        
        # Baixar imagem principal
        resposta = requests.get(url_imagem, timeout=30)
        resposta.raise_for_status()
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as img_temp:
            img_path = img_temp.name
            img_temp.write(resposta.content)
        
        # Criar overlay com textos no estilo Boca
        overlay_path = criar_overlay_boca(titulo, resumo, fontes)
        if not overlay_path:
            return None
        
        # Criar arquivo de vídeo temporário
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as video_temp:
            video_path = video_temp.name
        
        # Criar clip da imagem com pan/zoom
        clip_imagem = ImageClip(img_path, duration=VIDEO_DURATION)
        clip_imagem = aplicar_pan_zoom(clip_imagem)
        clip_imagem = clip_imagem.resize(width=VIDEO_SIZE[0])
        
        # Clip do overlay
        clip_overlay = ImageClip(overlay_path, duration=VIDEO_DURATION)
        clip_overlay = clip_overlay.set_position(('center', 'center'))
        
        # Combinar tudo
        video_final = CompositeVideoClip([clip_imagem, clip_overlay])
        video_final = video_final.set_fps(VIDEO_FPS)
        video_final = video_final.set_duration(VIDEO_DURATION)
        
        # Exportar vídeo (10 segundos)
        video_final.write_videofile(
            video_path,
            codec="libx264",
            audio=False,  # Você adicionará a música de 10s depois
            verbose=False,
            logger=None,
            threads=4,
            preset='fast'
        )
        
        print("✅ Vídeo gerado com sucesso - 10 segundos com pan/zoom")
        return video_path
        
    except Exception as e:
        print(f"❌ Erro ao gerar vídeo: {e}")
        return None
        
    finally:
        # Limpeza
        if fontes:
            for font_path in fontes.values():
                try:
                    if os.path.exists(font_path):
                        os.unlink(font_path)
                except:
                    pass
        
        if overlay_path and os.path.exists(overlay_path):
            try:
                os.unlink(overlay_path)
            except:
                pass
        
        if img_path and os.path.exists(img_path):
            try:
                os.unlink(img_path)
            except:
                pass

# ========================= FUNÇÕES DE UPLOAD E PUBLICAÇÃO =========================

def fazer_upload_cloudinary(arquivo_path):
    """Faz upload para Cloudinary"""
    try:
        print("☁️ Fazendo upload para Cloudinary...")
        resultado = cloudinary.uploader.upload(
            arquivo_path,
            resource_type="video",
            folder="boca_reels",
            timeout=300
        )
        return resultado['secure_url']
    except Exception as e:
        print(f"❌ Erro no upload: {e}")
        return None

def publicar_rede_social(url_video, legenda, plataforma):
    """Publica em Instagram ou Facebook"""
    try:
        if plataforma == "instagram":
            url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{INSTAGRAM_ID}/media"
            params = {
                "media_type": "REELS",
                "video_url": url_video,
                "caption": legenda[:2200],
                "access_token": META_API_TOKEN
            }
        else:  # facebook
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
        print(f"❌ Erro ao publicar no {plataforma}: {e}")
        return False

# ========================= WEBHOOK PRINCIPAL =========================

@app.route('/webhook-boca', methods=['POST'])
def webhook_receiver():
    print("🔔 Webhook recebido - BOCA NO TROMBONE")
    
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
            return jsonify({"erro": "Sem imagem de destaque"}), 400
        
        url_imagem = f"{WP_URL}/wp-json/wp/v2/media/{imagem_id}"
        resposta_imagem = requests.get(url_imagem, headers=HEADERS_WP, timeout=30)
        resposta_imagem.raise_for_status()
        url_imagem = resposta_imagem.json().get("source_url")
        
        # Gerar vídeo no estilo Boca (10 segundos)
        print("🎬 Gerando vídeo no estilo Boca no Trombone...")
        video_path = gerar_video_estilo_boca(url_imagem, titulo, resumo)
        if not video_path:
            return jsonify({"erro": "Falha ao gerar vídeo"}), 500
        
        # Fazer upload
        print("☁️ Fazendo upload do vídeo...")
        url_publica = fazer_upload_cloudinary(video_path)
        if not url_publica:
            return jsonify({"erro": "Falha no upload"}), 500
        
        # Criar legenda para redes sociais
        legenda = f"{titulo}\n\n{resumo}\n\n📖 Leia a matéria completa no site!\n\n#BocaNoTrombone #LitoralNorte #Noticias #SãoSebastião #Jornalismo"
        
        # Publicar nas redes
        print("📤 Publicando nas redes sociais...")
        instagram_ok = publicar_rede_social(url_publica, legenda, "instagram")
        facebook_ok = publicar_rede_social(url_publica, legenda, "facebook")
        
        if instagram_ok or facebook_ok:
            print("🎉 Publicação concluída com sucesso!")
            return jsonify({
                "sucesso": True,
                "mensagem": "Vídeo de 10s publicado com sucesso!",
                "url_video": url_publica
            }), 200
        else:
            return jsonify({"erro": "Falha na publicação"}), 500
            
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        return jsonify({"erro": str(e)}), 500
        
    finally:
        # Limpeza do arquivo de vídeo temporário
        if video_path and os.path.exists(video_path):
            try:
                os.unlink(video_path)
                print("🧹 Arquivo temporário removido")
            except Exception as e:
                print(f"⚠️ Erro na limpeza: {e}")

@app.route('/')
def home():
    return "🚀 BOCA NO TROMBONE - Sistema de Automação de Reels (10s)"

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
