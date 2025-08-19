# ==============================================================================
# BLOCO 1: IMPORTAÇÕES
# ==============================================================================
import os
import io
import json
import requests
import textwrap
import time
import tempfile
import numpy as np
from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
from base64 import b64encode
# Importação para criação de vídeo
import moviepy.editor as mpe

# ==============================================================================
# BLOCO 2: CONFIGURAÇÃO INICIAL
# ==============================================================================
load_dotenv()
app = Flask(__name__)

print("🚀 INICIANDO APLICAÇÃO BOCA NO TROMBONE v1.0 (Reels Edition)")

# Configs da Imagem/Vídeo
IMG_WIDTH, IMG_HEIGHT = 1080, 1920 # Proporção de Reels (9:16)
DURACAO_REELS = 7 # Duração do vídeo em segundos

# Configs do WordPress (usado para buscar detalhes do post)
WP_URL = os.getenv('WP_URL')
WP_USER = os.getenv('WP_USER')
WP_PASSWORD = os.getenv('WP_PASSWORD')
if all([WP_URL, WP_USER, WP_PASSWORD]):
    credentials = f"{WP_USER}:{WP_PASSWORD}"
    token_wp = b64encode(credentials.encode())
    HEADERS_WP = {'Authorization': f'Basic {token_wp.decode("utf-8")}'}
    print("✅ [CONFIG] Variáveis do WordPress carregadas.")
else:
    print("❌ [ERRO DE CONFIG] Faltando variáveis de ambiente do WordPress.")
    HEADERS_WP = {}

# Configs da API do Meta (BOCA NO TROMBONE)
# ATENÇÃO: Use variáveis de ambiente diferentes para este app
BOCA_META_API_TOKEN = os.getenv('BOCA_META_API_TOKEN')
BOCA_INSTAGRAM_ID = os.getenv('BOCA_INSTAGRAM_ID')
BOCA_FACEBOOK_PAGE_ID = os.getenv('BOCA_FACEBOOK_PAGE_ID')
GRAPH_API_VERSION = 'v19.0'
if all([BOCA_META_API_TOKEN, BOCA_INSTAGRAM_ID, BOCA_FACEBOOK_PAGE_ID]):
    print("✅ [CONFIG] Variáveis do Boca No Trombone carregadas.")
else:
    print("⚠️ [AVISO DE CONFIG] Faltando uma ou mais variáveis do Boca No Trombone.")

# ==============================================================================
# BLOCO 3: FUNÇÕES AUXILIARES
# ==============================================================================
def criar_video_reels_boca(url_imagem, titulo_post, url_logo):
    """
    Cria um vídeo curto (Reel) a partir de uma imagem de notícia para o Boca no Trombone.
    """
    print("🎬 [ETAPA 1/4] Iniciando criação do vídeo para o Reels (Boca)...")
    try:
        print("    - Baixando imagem da notícia...")
        response_img = requests.get(url_imagem, stream=True, timeout=15); response_img.raise_for_status()
        imagem_noticia = Image.open(io.BytesIO(response_img.content)).convert("RGBA")

        print("    - Baixando imagem do logo (Boca)...")
        response_logo = requests.get(url_logo, stream=True, timeout=15); response_logo.raise_for_status()
        logo = Image.open(io.BytesIO(response_logo.content)).convert("RGBA")

        # Cores e fontes (pode ajustar o design aqui se for diferente)
        cor_fundo_geral = "#f1f1f1" 
        cor_caixa_principal = "#003049"
        cor_detalhe = "#d62828"
        fonte_titulo = ImageFont.truetype("Anton-Regular.ttf", 75)
        fonte_arroba = ImageFont.truetype("Anton-Regular.ttf", 45)

        print("    - Montando o layout vertical...")
        imagem_frame = Image.new('RGBA', (IMG_WIDTH, IMG_HEIGHT), cor_fundo_geral)
        draw = ImageDraw.Draw(imagem_frame)

        # Imagem da notícia no topo
        img_w, img_h = 1000, 563 # 16:9
        imagem_noticia_resized = imagem_noticia.resize((img_w, img_h))
        pos_img_x = (IMG_WIDTH - img_w) // 2
        pos_img_y = 150
        imagem_frame.paste(imagem_noticia_resized, (pos_img_x, pos_img_y))

        # Caixa de texto na parte inferior
        raio_arredondado = 40
        draw.rounded_rectangle([(40, 800), (IMG_WIDTH - 40, IMG_HEIGHT - 150)], radius=raio_arredondado, fill=cor_detalhe)
        draw.rounded_rectangle([(50, 810), (IMG_WIDTH - 50, IMG_HEIGHT - 160)], radius=raio_arredondado, fill=cor_caixa_principal)

        # Logo centralizado sobre a caixa
        logo.thumbnail((300, 300))
        pos_logo_x = (IMG_WIDTH - logo.width) // 2
        pos_logo_y = 810 - (logo.height // 2)
        imagem_frame.paste(logo, (pos_logo_x, pos_logo_y), logo)
        
        print("    - Adicionando textos...")
        linhas_texto = textwrap.wrap(titulo_post.upper(), width=25)
        texto_junto = "\n".join(linhas_texto)
        draw.text((IMG_WIDTH / 2, 1250), texto_junto, font=fonte_titulo, fill=(255,255,255,255), anchor="mm", align="center")
        
        # <<< ALTERE O @ AQUI PARA O DO BOCA NO TROMBONE >>>
        draw.text((IMG_WIDTH / 2, 1680), "@BOCANOTROMBONELITORAL", font=fonte_arroba, fill=cor_caixa_principal, anchor="ms", align="center")

        print("    - Convertendo frame em clipe de vídeo...")
        frame_np = np.array(imagem_frame.convert('RGB'))
        video_clip = mpe.ImageClip(frame_np).set_duration(DURACAO_REELS)
        
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_video_file:
            temp_filename = temp_video_file.name
            video_clip.write_videofile(temp_filename, codec="libx264", fps=24, logger=None) # logger=None para limpar o output

        with open(temp_filename, "rb") as f:
            video_bytes = f.read()
        
        os.remove(temp_filename)

        print("✅ [ETAPA 1/4] Vídeo (Boca) criado com sucesso!")
        return video_bytes
        
    except Exception as e:
        print(f"❌ [ERRO] Falha crítica na criação do vídeo (Boca): {e}")
        return None

def upload_para_wordpress(bytes_video, nome_arquivo):
    print(f"⬆️  [ETAPA 2/4] Fazendo upload do vídeo para o WordPress...")
    try:
        url_wp_media = f"{WP_URL}/wp-json/wp/v2/media"
        headers_upload = HEADERS_WP.copy()
        headers_upload['Content-Disposition'] = f'attachment; filename={nome_arquivo}'
        headers_upload['Content-Type'] = 'video/mp4'
        
        response = requests.post(url_wp_media, headers=headers_upload, data=bytes_video, timeout=60)
        response.raise_for_status()
        link_video_publico = response.json()['source_url']
        
        print(f"✅ [ETAPA 2/4] Vídeo salvo no WordPress!")
        return link_video_publico
    except Exception as e:
        print(f"❌ [ERRO] Falha ao fazer upload para o WordPress: {e}")
        return None

def publicar_reel_no_instagram(url_video, legenda):
    print("📤 [ETAPA 3/4] Publicando Reel no Instagram (Boca)...")
    if not all([BOCA_META_API_TOKEN, BOCA_INSTAGRAM_ID]):
        print("    - ⚠️ Publicação pulada: Faltando variáveis de ambiente do Instagram (Boca).")
        return False

    try:
        print("    - [Passo 1/3] Criando contêiner de mídia...")
        url_container = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{BOCA_INSTAGRAM_ID}/media"
        params_container = {
            'media_type': 'REELS',
            'video_url': url_video,
            'caption': legenda,
            'access_token': BOCA_META_API_TOKEN
        }
        r_container = requests.post(url_container, params=params_container, timeout=30); r_container.raise_for_status()
        id_criacao = r_container.json()['id']
        
        print("    - [Passo 2/3] Verificando status do upload...")
        for _ in range(20): # Tenta por até 100 segundos
            url_status = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{id_criacao}"
            params_status = {'fields': 'status_code', 'access_token': BOCA_META_API_TOKEN}
            r_status = requests.get(url_status, params=params_status, timeout=20); r_status.raise_for_status()
            status = r_status.json().get('status_code')
            if status == 'FINISHED': break
            if status == 'ERROR': raise Exception("API retornou erro no processamento do vídeo.")
            time.sleep(5)
        else:
            raise Exception("Timeout: Vídeo não processado a tempo.")

        print("    - [Passo 3/3] Publicando o contêiner...")
        url_publicacao = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{BOCA_INSTAGRAM_ID}/media_publish"
        params_publicacao = {'creation_id': id_criacao, 'access_token': BOCA_META_API_TOKEN}
        r_publish = requests.post(url_publicacao, params=params_publicacao, timeout=30); r_publish.raise_for_status()
        
        print("✅ [ETAPA 3/4] Reel publicado no Instagram (Boca) com sucesso!")
        return True
    except Exception as e:
        print(f"❌ [ERRO INSTAGRAM BOCA] Falha ao publicar Reel: {e}")
        if hasattr(e, 'response'): print(f"    - Resposta da API: {e.response.text}")
        return False

def publicar_video_no_facebook(url_video, legenda):
    print("📤 [ETAPA 4/4] Publicando vídeo no Facebook (Boca)...")
    if not all([BOCA_META_API_TOKEN, BOCA_FACEBOOK_PAGE_ID]):
        print("    - ⚠️ Publicação pulada: Faltando variáveis de ambiente do Facebook (Boca).")
        return False
    try:
        url_post_video = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{BOCA_FACEBOOK_PAGE_ID}/videos"
        params = {'file_url': url_video, 'description': legenda, 'access_token': BOCA_META_API_TOKEN}
        r = requests.post(url_post_video, params=params, timeout=60); r.raise_for_status()
        print("✅ [ETAPA 4/4] Vídeo publicado no Facebook (Boca) com sucesso!")
        return True
    except Exception as e:
        print(f"❌ [ERRO FACEBOOK BOCA] Falha ao publicar vídeo: {e}")
        if hasattr(e, 'response'): print(f"    - Resposta da API: {e.response.text}")
        return False

# ==============================================================================
# BLOCO 4: O MAESTRO (RECEPTOR DO WEBHOOK)
# ==============================================================================
@app.route('/webhook-boca', methods=['POST'])
def webhook_boca_receiver():
    print("\n" + "="*50)
    print("🔔 [WEBHOOK BOCA] Webhook recebido do app Voz do Litoral!")
    
    try:
        # A lógica para extrair dados do webhook é a mesma do app anterior
        dados_brutos = request.json
        post_info = dados_brutos.get('post', {})
        post_id = post_info.get('ID')
        post_type = post_info.get('post_type')
        post_parent = post_info.get('post_parent')

        if post_type == 'revision' and post_parent:
            post_id = post_parent
        elif not post_id:
            post_id = dados_brutos.get('post_id')

        if not post_id: raise ValueError("ID do post final não pôde ser determinado.")

        print(f"✅ [WEBHOOK BOCA] ID do post extraído: {post_id}")
        
        print(f"🔍 [API WP] Buscando detalhes do post ID: {post_id}...")
        url_api_post = f"{WP_URL}/wp-json/wp/v2/posts/{post_id}"
        response_post = requests.get(url_api_post, headers=HEADERS_WP, timeout=15); response_post.raise_for_status()
        post_data = response_post.json()

        titulo_noticia = BeautifulSoup(post_data.get('title', {}).get('rendered', ''), 'html.parser').get_text()
        resumo_noticia = BeautifulSoup(post_data.get('excerpt', {}).get('rendered', ''), 'html.parser').get_text(strip=True)
        id_imagem_destaque = post_data.get('featured_media')
        
        # <<< ALTERE A URL DO LOGO DO BOCA AQUI >>>
        url_logo_boca = "https://jornalbocanotrombone.com.br/wp-content/uploads/2024/03/cropped-BOCA-NO-TROMBONE-LITORAL-2.png"

        if not id_imagem_destaque or id_imagem_destaque == 0:
            return jsonify({"status": "ignorado_sem_imagem"}), 200
            
        url_api_media = f"{WP_URL}/wp-json/wp/v2/media/{id_imagem_destaque}"
        response_media = requests.get(url_api_media, headers=HEADERS_WP, timeout=15); response_media.raise_for_status()
        url_imagem_destaque = response_media.json().get('source_url')
            
    except Exception as e:
        print(f"❌ [ERRO CRÍTICO BOCA] Falha ao processar dados do webhook: {e}")
        return jsonify({"status": "erro_processamento_wp_boca"}), 500

    print("\n🚀 INICIANDO FLUXO DE PUBLICAÇÃO DE REELS (BOCA)...")
    
    video_gerado_bytes = criar_video_reels_boca(url_imagem_destaque, titulo_noticia, url_logo_boca)
    if not video_gerado_bytes: return jsonify({"status": "erro_criacao_video_boca"}), 500
    
    nome_do_arquivo = f"reel_boca_{post_id}.mp4"
    link_wp_video = upload_para_wordpress(video_gerado_bytes, nome_do_arquivo)
    if not link_wp_video: return jsonify({"status": "erro_upload_wordpress_boca"}), 500

    legenda_final = f"{titulo_noticia}\n\n{resumo_noticia}\n\nLeia a matéria completa em nosso site. Link na bio!\n\n#noticias #litoralnorte #bocanotrombone #jornalismo #reels"
    
    sucesso_ig = publicar_reel_no_instagram(link_wp_video, legenda_final)
    sucesso_fb = publicar_video_no_facebook(link_wp_video, legenda_final)

    if sucesso_ig or sucesso_fb:
        print("🎉 [SUCESSO] Automação do Boca no Trombone concluída!")
        return jsonify({"status": "sucesso_publicacao_boca"}), 200
    else:
        print("😭 [FALHA] Nenhuma publicação do Boca no Trombone foi bem-sucedida.")
        return jsonify({"status": "erro_publicacao_redes_boca"}), 500

# ==============================================================================
# BLOCO 5: INICIALIZAÇÃO
# ==============================================================================
@app.route('/')
def health_check():
    return "Serviço de automação Boca No Trombone v1.0 (Reels Edition) está no ar.", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10001)) # Use uma porta diferente, ex: 10001
    app.run(host='0.0.0.0', port=port)
