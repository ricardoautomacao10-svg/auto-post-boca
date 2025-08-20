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
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import io

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
INSTAGRAM_ID = os.getenv('INSTAGRAM_ID')
FACEBOOK_PAGE_ID = os.getenv('FACEBOOK_PAGE_ID') 
META_API_TOKEN = os.getenv('META_API_TOKEN')
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

# Configurações de fontes LOCAIS
FONTES_LOCAIS = {
    "TITULO": "Anton-Regular.ttf",
    "TEXTO": "Roboto-Bold.ttf", 
    "RODAPE": "Roboto-Black.ttf"
}

# ========================= FUNÇÕES PRINCIPAIS =========================

def carregar_fontes_locais():
    """Carrega fontes locais da raiz do projeto"""
    fontes = {}
    try:
        for nome, arquivo in FONTES_LOCAIS.items():
            caminho_fonte = os.path.join(os.path.dirname(__file__), arquivo)
            
            if os.path.exists(caminho_fonte):
                with open(caminho_fonte, 'rb') as f_origem:
                    with tempfile.NamedTemporaryFile(suffix='.ttf', delete=False) as f_temp:
                        f_temp.write(f_origem.read())
                        fontes[nome] = f_temp.name
                print(f"✅ Fonte {nome} carregada: {arquivo}")
            else:
                print(f"⚠️ Fonte {arquivo} não encontrada")
                fontes[nome] = None
        
        return fontes
        
    except Exception as e:
        print(f"❌ Erro ao carregar fontes: {e}")
        return None

def criar_overlay_boca(titulo, resumo, caminho_fontes):
    """Cria overlay no estilo Boca no Trombone"""
    try:
        overlay = Image.new('RGBA', VIDEO_SIZE, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Configurações de fonte
        try:
            if caminho_fontes.get("TEXTO"):
                fonte = ImageFont.truetype(caminho_fontes["TEXTO"], 45)
            else:
                fonte = ImageFont.load_default()
        except:
            fonte = ImageFont.load_default()
        
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

        # Título
        titulo = titulo.upper()[:50]
        y_pos = VIDEO_SIZE[1]//2 - 50
        x_pos = 100
        
        draw.text((x_pos, y_pos), titulo, font=fonte, fill=cor_texto)
        
        # Rodapé
        rodape = "@BOCANOTROMBONELITORAL"
        y_pos = VIDEO_SIZE[1] - 120
        x_pos = (VIDEO_SIZE[0] - 600) // 2
        
        draw.rectangle([(x_pos-20, y_pos-10), (x_pos+600, y_pos+50)], fill=cor_texto)
        draw.text((x_pos, y_pos), rodape, font=fonte, fill=(255, 255, 255))
        
        # Salvar overlay
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as overlay_temp:
            overlay_path = overlay_temp.name
            overlay.save(overlay_path, 'PNG')
        
        return overlay_path
        
    except Exception as e:
        print(f"❌ Erro ao criar overlay: {e}")
        return None

def gerar_video_simples(url_imagem, titulo, resumo):
    """Gera vídeo usando PIL + OpenCV - método confiável"""
    try:
        print("🎬 Gerando vídeo com método simplificado...")
        
        # Baixa imagem
        resposta = requests.get(url_imagem, timeout=30)
        resposta.raise_for_status()
        
        # Abre a imagem e redimensiona
        img = Image.open(io.BytesIO(resposta.content))
        img = img.resize(VIDEO_SIZE)
        
        # Carrega fontes
        fontes = carregar_fontes_locais()
        
        # Cria overlay
        overlay_path = criar_overlay_boca(titulo, resumo, fontes or {})
        
        # Combina imagem e overlay
        if overlay_path and os.path.exists(overlay_path):
            overlay_img = Image.open(overlay_path)
            img.paste(overlay_img, (0, 0), overlay_img)
        
        # Converte para array numpy (OpenCV)
        frame = np.array(img)
        
        # Converte RGB para BGR (OpenCV usa BGR)
        import cv2
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        # Cria arquivo de vídeo temporário
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as video_temp:
            video_path = video_temp.name
        
        # Cria vídeo com mesmo frame repetido
        out = cv2.VideoWriter(
            video_path, 
            cv2.VideoWriter_fourcc(*'mp4v'), 
            VIDEO_FPS, 
            VIDEO_SIZE
        )
        
        # Adiciona frames para durar 10 segundos
        for _ in range(VIDEO_DURATION * VIDEO_FPS):
            out.write(frame)
        
        out.release()
        print("✅ Vídeo gerado com sucesso!")
        return video_path
        
    except Exception as e:
        print(f"❌ Erro ao gerar vídeo: {e}")
        return None
        
    finally:
        # Limpeza
        if 'overlay_path' in locals() and overlay_path and os.path.exists(overlay_path):
            try:
                os.unlink(overlay_path)
            except:
                pass

def fazer_upload_cloudinary(arquivo_path):
    """Upload para Cloudinary"""
    try:
        print("☁️ Fazendo upload para Cloudinary...")
        resultado = cloudinary.uploader.upload(
            arquivo_path, 
            resource_type="video", 
            folder="boca_reels",
            timeout=300
        )
        print("✅ Upload concluído!")
        return resultado['secure_url']
    except Exception as e:
        print(f"❌ Erro no upload: {e}")
        return None

def publicar_rede_social(url_video, legenda, plataforma):
    """Publica nas redes sociais"""
    try:
        print(f"📤 Publicando no {plataforma}...")
        
        if plataforma == "instagram":
            url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{INSTAGRAM_ID}/media"
            params = {
                "media_type": "REELS", 
                "video_url": url_video, 
                "caption": legenda[:2200], 
                "access_token": META_API_TOKEN
            }
        else:
            url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{FACEBOOK_PAGE_ID}/videos"
            params = {
                "file_url": url_video, 
                "description": legenda, 
                "access_token": META_API_TOKEN
            }
        
        resposta = requests.post(url, data=params, timeout=60)
        resposta.raise_for_status()
        print(f"✅ Publicado no {plataforma}!")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao publicar no {plataforma}: {e}")
        return False

# ========================= ROTAS PRINCIPAIS =========================

@app.route('/webhook-boca', methods=['POST'])
def webhook_receiver():
    print("=" * 60)
    print("🔔 WEBHOOK RECEBIDO - INICIANDO PROCESSAMENTO")
    print("=" * 60)
    
    video_path = None
    try:
        # Verifica variáveis de ambiente primeiro
        variaveis_necessarias = [
            'WP_URL', 'WP_USER', 'WP_PASSWORD', 
            'INSTAGRAM_ID', 'FACEBOOK_PAGE_ID', 'META_API_TOKEN',
            'CLOUDINARY_CLOUD_NAME', 'CLOUDINARY_API_KEY', 'CLOUDINARY_API_SECRET'
        ]
        
        variaveis_faltantes = [var for var in variaveis_necessarias if not os.getenv(var)]
        if variaveis_faltantes:
            print(f"❌ VARIÁVEIS FALTANDO: {variaveis_faltantes}")
            return jsonify({"erro": f"Variáveis faltando: {variaveis_faltantes}"}), 500
        
        dados = request.json
        print(f"📦 Dados recebidos: {dados}")
        
        if not dados:
            print("❌ Nenhum dado JSON recebido")
            return jsonify({"erro": "Nenhum dado recebido"}), 400
            
        post_id = dados.get("post_id")
        print(f"📝 Post ID: {post_id}")
        
        if not post_id:
            print("❌ Post ID não encontrado")
            return jsonify({"erro": "Post ID não fornecido"}), 400
        
        # Buscar dados do post
        print("🌐 Buscando dados do WordPress...")
        url_post = f"{WP_URL}/wp-json/wp/v2/posts/{post_id}"
        resposta = requests.get(url_post, headers=HEADERS_WP, timeout=30)
        resposta.raise_for_status()
        post = resposta.json()
        
        # Extrair título e resumo
        titulo = BeautifulSoup(post.get('title', {}).get('rendered', ''), 'html.parser').get_text()
        resumo = BeautifulSoup(post.get('excerpt', {}).get('rendered', ''), 'html.parser').get_text(strip=True)
        print(f"📰 Título: {titulo}")
        print(f"📋 Resumo: {resumo}")
        
        # Buscar imagem
        imagem_id = post.get('featured_media')
        if not imagem_id:
            print("❌ Post sem imagem destacada")
            return jsonify({"erro": "Sem imagem de destaque"}), 400
        
        url_imagem = f"{WP_URL}/wp-json/wp/v2/media/{imagem_id}"
        resposta_imagem = requests.get(url_imagem, headers=HEADERS_WP, timeout=30)
        resposta_imagem.raise_for_status()
        url_imagem = resposta_imagem.json().get("source_url")
        print(f"🖼️ URL da imagem: {url_imagem}")
        
        # Gerar vídeo
        video_path = gerar_video_simples(url_imagem, titulo, resumo)
        if not video_path:
            return jsonify({"erro": "Falha ao gerar vídeo"}), 500
        
        # Upload
        url_publica = fazer_upload_cloudinary(video_path)
        if not url_publica:
            return jsonify({"erro": "Falha no upload"}), 500
        
        print(f"🔗 URL pública do vídeo: {url_publica}")
        
        # Publicar
        legenda = f"{titulo}\n\n{resumo}\n\n📖 Leia a matéria completa no site!\n\n#BocaNoTrombone #LitoralNorte #Noticias #SãoSebastião"
        
        instagram_ok = publicar_rede_social(url_publica, legenda, "instagram")
        facebook_ok = publicar_rede_social(url_publica, legenda, "facebook")
        
        if instagram_ok or facebook_ok:
            print("🎉 PUBLICAÇÃO CONCLUÍDA COM SUCESSO!")
            return jsonify({
                "sucesso": True,
                "mensagem": "Vídeo publicado com sucesso!",
                "url_video": url_publica
            }), 200
        else:
            print("❌ Nenhuma publicação foi bem-sucedida")
            return jsonify({"erro": "Falha na publicação"}), 500
            
    except Exception as e:
        print(f"❌ ERRO GERAL: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"erro": str(e)}), 500
        
    finally:
        if video_path and os.path.exists(video_path):
            try:
                os.unlink(video_path)
                print("🧹 Arquivo temporário removido")
            except Exception as e:
                print(f"⚠️ Erro na limpeza: {e}")

@app.route('/teste-integracao', methods=['GET'])
def teste_integracao():
    """Rota para testar todas as integrações"""
    print("🧪 Iniciando teste de integração")
    
    resultados = {
        "wordpress": False,
        "cloudinary": False, 
        "meta": False,
        "fontes": False
    }
    
    # Teste WordPress
    try:
        if all([WP_URL, WP_USER, WP_PASSWORD]):
            resultados["wordpress"] = True
            print("✅ Variáveis WordPress OK")
        else:
            print("❌ Variáveis WordPress incompletas")
    except Exception as e:
        print(f"❌ Erro WordPress: {e}")
    
    # Teste Cloudinary
    try:
        cloudinary_vars = ['CLOUDINARY_CLOUD_NAME', 'CLOUDINARY_API_KEY', 'CLOUDINARY_API_SECRET']
        if all([os.getenv(var) for var in cloudinary_vars]):
            resultados["cloudinary"] = True
            print("✅ Variáveis Cloudinary OK")
        else:
            print("❌ Variáveis Cloudinary incompletas")
    except Exception as e:
        print(f"❌ Erro Cloudinary: {e}")
    
    # Teste Meta
    try:
        if all([INSTAGRAM_ID, FACEBOOK_PAGE_ID, META_API_TOKEN]):
            resultados["meta"] = True
            print("✅ Variáveis Meta OK")
        else:
            print("❌ Variáveis Meta incompletas")
    except Exception as e:
        print(f"❌ Erro Meta: {e}")
    
    # Teste Fontes
    try:
        fontes = carregar_fontes_locais()
        if fontes:
            resultados["fontes"] = True
            print("✅ Fontes carregadas OK")
        else:
            print("❌ Erro ao carregar fontes")
    except Exception as e:
        print(f"❌ Erro fontes: {e}")
    
    return jsonify({
        "status": "teste_concluido",
        "resultados": resultados,
        "timestamp": time.time()
    })

@app.route('/')
def home():
    return "🚀 BOCA NO TROMBONE - Sistema de Automação de Reels (10s)"

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "online",
        "service": "boca-no-trombone",
        "timestamp": time.time()
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
