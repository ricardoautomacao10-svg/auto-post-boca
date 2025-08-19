# ==============================================================================
# BLOCO 1: IMPORTAÇÕES
# ==============================================================================
import os
import io
import json
import requests
import textwrap
from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
from base64 import b64encode

# ==============================================================================
# BLOCO 2: CONFIGURAÇÃO INICIAL
# ==============================================================================
load_dotenv()
app = Flask(__name__)

print("🚀 INICIANDO APLICAÇÃO DE AUTOMAÇÃO v3.2 (Voz do Litoral - Final)")

# Configs da Imagem
IMG_WIDTH, IMG_HEIGHT = 1080, 1080

# Configs do WordPress
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

# Configs da API do Meta (usando os nomes de variáveis originais)
META_API_TOKEN = os.getenv('META_API_TOKEN')
INSTAGRAM_ID = os.getenv('INSTAGRAM_ID')
FACEBOOK_PAGE_ID = os.getenv('FACEBOOK_PAGE_ID')
if all([META_API_TOKEN, INSTAGRAM_ID, FACEBOOK_PAGE_ID]):
    print("✅ [CONFIG] Variáveis do Voz do Litoral carregadas.")
else:
    print("⚠️ [AVISO DE CONFIG] Faltando uma ou mais variáveis do Voz do Litoral.")

# ==============================================================================
# BLOCO 3: FUNÇÕES AUXILIARES
# ==============================================================================
def criar_imagem_post(url_imagem, titulo_post, url_logo):
    print("🎨 [ETAPA 1/4] Iniciando criação da imagem...")
    try:
        response_img = requests.get(url_imagem, stream=True, timeout=15); response_img.raise_for_status()
        imagem_noticia = Image.open(io.BytesIO(response_img.content)).convert("RGBA")
        
        response_logo = requests.get(url_logo, stream=True, timeout=15); response_logo.raise_for_status()
        logo = Image.open(io.BytesIO(response_logo.content)).convert("RGBA")

        cor_fundo_geral = (255, 255, 255, 255)
        cor_fundo_texto = "#0d1b2a"
        cor_vermelha = "#d90429"
        fonte_titulo = ImageFont.truetype("Anton-Regular.ttf", 50)
        fonte_arroba = ImageFont.truetype("Anton-Regular.ttf", 30)

        imagem_final = Image.new('RGBA', (IMG_WIDTH, IMG_HEIGHT), cor_fundo_geral)
        draw = ImageDraw.Draw(imagem_final)

        img_w, img_h = 980, 551
        imagem_noticia_resized = imagem_noticia.resize((img_w, img_h))
        pos_img_x = (IMG_WIDTH - img_w) // 2
        imagem_final.paste(imagem_noticia_resized, (pos_img_x, 50))

        raio_arredondado = 40
        draw.rounded_rectangle([(40, 610), (IMG_WIDTH - 40, IMG_HEIGHT - 40)], radius=raio_arredondado, fill=cor_vermelha)
        draw.rounded_rectangle([(50, 620), (IMG_WIDTH - 50, IMG_HEIGHT - 50)], radius=raio_arredondado, fill=cor_fundo_texto)

        logo.thumbnail((220, 220))
        pos_logo_x = (IMG_WIDTH - logo.width) // 2
        pos_logo_y = 620 - (logo.height // 2)
        imagem_final.paste(logo, (pos_logo_x, pos_logo_y), logo)
        
        linhas_texto = textwrap.wrap(titulo_post.upper(), width=32)
        texto_junto = "\n".join(linhas_texto)
        draw.text((IMG_WIDTH / 2, 800), texto_junto, font=fonte_titulo, fill=(255,255,255,255), anchor="mm", align="center")
        draw.text((IMG_WIDTH / 2, 980), "@VOZDOLITORALNORTE", font=fonte_arroba, fill=(255,255,255,255), anchor="ms", align="center")

        buffer_saida = io.BytesIO()
        imagem_final.convert('RGB').save(buffer_saida, format='JPEG', quality=95)
        print("✅ [ETAPA 1/4] Imagem criada com sucesso!")
        return buffer_saida.getvalue()
        
    except Exception as e:
        print(f"❌ [ERRO] Falha crítica na criação da imagem: {e}")
        return None

def upload_para_wordpress(bytes_imagem, nome_arquivo):
    print(f"⬆️  [ETAPA 2/4] Fazendo upload para o WordPress...")
    try:
        url_wp_media = f"{WP_URL}/wp-json/wp/v2/media"
        headers_upload = HEADERS_WP.copy()
        headers_upload['Content-Disposition'] = f'attachment; filename={nome_arquivo}'
        headers_upload['Content-Type'] = 'image/jpeg'
        response = requests.post(url_wp_media, headers_upload, data=bytes_imagem, timeout=30)
        response.raise_for_status()
        link_imagem_publica = response.json()['source_url']
        print(f"✅ [ETAPA 2/4] Imagem salva no WordPress!")
        return link_imagem_publica
    except Exception as e:
        print(f"❌ [ERRO] Falha ao fazer upload para o WordPress: {e}")
        return None

def publicar_no_instagram(url_imagem, legenda):
    print("📤 [ETAPA 3/4] Publicando no Instagram (Voz)...")
    if not all([META_API_TOKEN, INSTAGRAM_ID]): 
        return False
    try:
        url_container = f"https://graph.facebook.com/v19.0/{INSTAGRAM_ID}/media"
        params_container = {'image_url': url_imagem, 'caption': legenda, 'access_token': META_API_TOKEN}
        r_container = requests.post(url_container, params=params_container, timeout=20)
        r_container.raise_for_status()
        id_criacao = r_container.json()['id']
        
        url_publicacao = f"https://graph.facebook.com/v19.0/{INSTAGRAM_ID}/media_publish"
        params_publicacao = {'creation_id': id_criacao, 'access_token': META_API_TOKEN}
        r_publish = requests.post(url_publicacao, params=params_publicacao, timeout=20)
        r_publish.raise_for_status()
        
        print("✅ [ETAPA 3/4] Post publicado no Instagram (Voz) com sucesso!")
        return True
    except Exception as e:
        print(f"❌ [ERRO INSTAGRAM] Falha ao publicar: {e}")
        if hasattr(e, 'response'): print(f"    - Resposta da API: {e.response.text}")
        return False

def publicar_no_facebook(url_imagem, legenda):
    print("📤 [ETAPA 4/4] Publicando no Facebook (Voz)...")
    if not all([META_API_TOKEN, FACEBOOK_PAGE_ID]): 
        return False
    try:
        url_post_foto = f"https://graph.facebook.com/v19.0/{FACEBOOK_PAGE_ID}/photos"
        params = {'url': url_imagem, 'message': legenda, 'access_token': META_API_TOKEN}
        r = requests.post(url_post_foto, params=params, timeout=20)
        r.raise_for_status()
        print("✅ [ETAPA 4/4] Post publicado no Facebook (Voz) com sucesso!")
        return True
    except Exception as e:
        print(f"❌ [ERRO FACEBOOK] Falha ao publicar: {e}")
        if hasattr(e, 'response'): print(f"    - Resposta da API: {e.response.text}")
        return False

# ==============================================================================
# BLOCO 4: O MAESTRO (RECEPTOR DO WEBHOOK)
# ==============================================================================
@app.route('/webhook-receiver', methods=['POST'])
def webhook_receiver():
    print("\n" + "="*50)
    print("🔔 [WEBHOOK] Webhook recebido do WordPress!")
    
    try:
        dados_brutos = request.json
        post_info = dados_brutos.get('post', {})
        post_id = post_info.get('ID')
        post_type = post_info.get('post_type')
        post_parent = post_info.get('post_parent')

        if post_type == 'revision' and post_parent:
            post_id = post_parent
        elif not post_id:
             post_id = dados_brutos.get('post_id')

        if not post_id:
            raise ValueError("ID do post final não pôde ser determinado.")

        url_api_post = f"{WP_URL}/wp-json/wp/v2/posts/{post_id}"
        response_post = requests.get(url_api_post, headers=HEADERS_WP, timeout=15)
        
        if response_post.status_code != 200:
            print(f"    - ⚠️ AVISO: Post ID {post_id} não encontrado (status {response_post.status_code}). Ignorando.")
            return jsonify({"status": "post_nao_encontrado"}), 200
        
        post_data = response_post.json()

        if post_data.get('status') != 'publish':
            print(f"    - ⚠️ AVISO: Post ID {post_id} não está publicado. Ignorando.")
            return jsonify({"status": "post_nao_publicado"}), 200

        titulo_noticia = BeautifulSoup(post_data.get('title', {}).get('rendered', ''), 'html.parser').get_text()
        resumo_noticia = BeautifulSoup(post_data.get('excerpt', {}).get('rendered', ''), 'html.parser').get_text(strip=True)
        id_imagem_destaque = post_data.get('featured_media')
        
        url_logo = "http://jornalvozdolitoral.com/wp-content/uploads/2025/08/novo-logo-1.png"

        if not id_imagem_destaque or id_imagem_destaque == 0:
            print("    - ⚠️ AVISO: Post não tem imagem de destaque. Ignorando.")
            return jsonify({"status": "sem_imagem_destaque"}), 200
            
        url_api_media = f"{WP_URL}/wp-json/wp/v2/media/{id_imagem_destaque}"
        response_media = requests.get(url_api_media, headers=HEADERS_WP, timeout=15); response_media.raise_for_status()
        url_imagem_destaque = response_media.json().get('source_url')
            
    except Exception as e:
        print(f"❌ [ERRO CRÍTICO] Falha ao processar dados do webhook: {e}")
        return jsonify({"status": "erro_processamento_wp"}), 500

    print("\n🚀 INICIANDO FLUXO DE PUBLICAÇÃO (VOZ DO LITORAL)...")
    
    imagem_gerada_bytes = criar_imagem_post(url_imagem_destaque, titulo_noticia, url_logo)
    if not imagem_gerada_bytes: return jsonify({"status": "erro_criacao_imagem"}), 500
    
    nome_do_arquivo = f"post_social_{post_id}.jpg"
    link_wp = upload_para_wordpress(imagem_gerada_bytes, nome_do_arquivo)
    if not link_wp: return jsonify({"status": "erro_upload_wordpress"}), 500

    legenda_final = f"{titulo_noticia}\n\n{resumo_noticia}\n\nLeia a matéria completa em nosso site. Link na bio!\n\n#noticias #litoralnorte #brasil #jornalismo"
    
    sucesso_ig = publicar_no_instagram(link_wp, legenda_final)
    sucesso_fb = publicar_no_facebook(link_wp, legenda_final)

    # ==========================================================
    # BLOCO DE ENCAMINHAMENTO
    # ==========================================================
    print("\n📬 ENCAMINHANDO >> Redirecionando webhook para a automação do Boca No Trombone...")
    url_webhook_boca = "https://auto-post-boca.onrender.com/webhook-boca"
    try:
        forward_response = requests.post(url_webhook_boca, json=request.json, timeout=15)
        print(f"    - Resposta do servidor Boca: Status {forward_response.status_code}")
    except Exception as e:
        print(f"    - ⚠️ AVISO: Falha ao redirecionar webhook para o Boca: {e}")
    # ==========================================================

    if sucesso_ig or sucesso_fb:
        print("🎉 [SUCESSO] Automação do Voz do Litoral concluída!")
        return jsonify({"status": "sucesso_publicacao_voz"}), 200
    else:
        print("😭 [FALHA] Nenhuma publicação do Voz do Litoral foi bem-sucedida.")
        return jsonify({"status": "erro_publicacao_redes_voz"}), 500

# ==============================================================================
# BLOCO 5: INICIALIZAÇÃO
# ==============================================================================
@app.route('/')
def health_check():
    return "Serviço de automação Voz do Litoral v3.2 (Final) está no ar.", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
