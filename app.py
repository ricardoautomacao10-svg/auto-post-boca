# ==============================================================================
# BLOCO 1: IMPORTAÇÕES
# ==============================================================================
import os
import time
import json
import requests
from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from base64 import b64encode

# Importações para a API de Vídeo (Shotstack)
from shotstack_sdk.api import edit_api
from shotstack_sdk.model.edit import Edit
from shotstack_sdk.model.output import Output
from shotstack_sdk.model.timeline import Timeline
from shotstack_sdk.model.track import Track
from shotstack_sdk.model.clip import Clip
from shotstack_sdk.model.image_asset import ImageAsset
from shotstack_sdk.model.title_asset import TitleAsset
# ==========================================================
# CORREÇÃO APLICADA AQUI: Importando o objeto 'Offset'
# ==========================================================
from shotstack_sdk.model.offset import Offset
from shotstack_sdk.configuration import Configuration
from shotstack_sdk.api_client import ApiClient

# ==============================================================================
# BLOCO 2: CONFIGURAÇÃO INICIAL
# ==============================================================================
load_dotenv()
app = Flask(__name__)

print("🚀 INICIANDO APLICAÇÃO BOCA NO TROMBONE v1.5 (Correção Final)")

# --- Configs do WordPress ---
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

# --- Configs do Meta para o BOCA NO TROMBONE ---
META_API_TOKEN_BOCA = os.getenv('META_API_TOKEN_BOCA')
INSTAGRAM_ID_BOCA = os.getenv('INSTAGRAM_ID_BOCA')
FACEBOOK_PAGE_ID_BOCA = os.getenv('FACEBOOK_PAGE_ID_BOCA')
if all([META_API_TOKEN_BOCA, INSTAGRAM_ID_BOCA, FACEBOOK_PAGE_ID_BOCA]):
    print("✅ [CONFIG] Variáveis do Boca No Trombone carregadas.")
else:
    print("❌ [ERRO DE CONFIG] Faltando variáveis do Boca No Trombone.")

# --- CONFIG do Shotstack (API de Vídeo) ---
SHOTSTACK_API_KEY = os.getenv('SHOTSTACK_API_KEY')
SHOTSTACK_API_URL = 'https://api.shotstack.io/v1'
if SHOTSTACK_API_KEY:
    print("✅ [CONFIG] Chave da API de Vídeo (Shotstack) carregada.")
    config = Configuration(host=SHOTSTACK_API_URL)
    config.api_key['x-api-key'] = SHOTSTACK_API_KEY
    api_client = ApiClient(config)
    api_instance = edit_api.EditApi(api_client)
else:
    print("❌ [ERRO DE CONFIG] Faltando a chave da API do Shotstack.")

# ==============================================================================
# BLOCO 3: FUNÇÕES DE PUBLICAÇÃO
# ==============================================================================

def criar_video_reel(url_imagem_noticia, titulo_noticia, url_logo_boca):
    print("🎬 [ETAPA 1/3] Iniciando criação do vídeo Reel...")
    if not SHOTSTACK_API_KEY:
        return None

    image_asset = ImageAsset(src=url_imagem_noticia)
    clip_imagem = Clip(asset=image_asset, start=0.0, length=12.0, effect="zoomIn")
    title_asset = TitleAsset(text=titulo_noticia.upper(), style="minimal", color="#FFFFFF", background="#d90429", size="medium")
    clip_titulo = Clip(asset=title_asset, start=1.0, length=10.0, position="bottom")
    logo_asset = ImageAsset(src=url_logo_boca)
    
    # ==========================================================
    # CORREÇÃO APLICADA AQUI: Usando o objeto 'Offset'
    # ==========================================================
    logo_offset = Offset(x=-0.4, y=-0.4)
    clip_logo = Clip(asset=logo_asset, start=0.5, length=11.0, position="topLeft", scale=0.3, offset=logo_offset)

    timeline = Timeline(tracks=[Track(clips=[clip_imagem]), Track(clips=[clip_titulo]), Track(clips=[clip_logo])])
    output = Output(format="mp4", resolution="1080")
    edit = Edit(timeline=timeline, output=output)

    try:
        print("    - Enviando requisição para a API de vídeo...")
        api_response = api_instance.post_render(edit)
        render_id = api_response['response']['id']
        print(f"    - Renderização iniciada com ID: {render_id}")

        print("    - Aguardando finalização do vídeo...")
        for i in range(20):
            status_response = api_instance.get_render(render_id)
            status = status_response['response']['status']
            print(f"    - Tentativa {i+1}/20: Status atual: {status.upper()}")
            if status == "done":
                video_url = status_response['response']['url']
                print(f"✅ [ETAPA 1/3] Vídeo criado com sucesso! URL: {video_url}")
                return video_url
            elif status in ["failed", "cancelled"]:
                print("❌ [ERRO] A renderização do vídeo falhou.")
                return None
            time.sleep(10)
        print("❌ [ERRO] Tempo de espera para renderização do vídeo excedido.")
        return None
    except Exception as e:
        print(f"❌ [ERRO] Falha na comunicação com a API de vídeo: {e}")
        return None

def publicar_reel_instagram(video_url, legenda):
    print("📤 [ETAPA 2/3] Publicando Reel no Instagram...")
    try:
        url_container = f"https://graph.facebook.com/v19.0/{INSTAGRAM_ID_BOCA}/media"
        params_container = {'media_type': 'REELS', 'video_url': video_url, 'caption': legenda, 'access_token': META_API_TOKEN_BOCA}
        r_container = requests.post(url_container, params=params_container, timeout=30)
        r_container.raise_for_status()
        id_criacao = r_container.json()['id']
        
        for i in range(15):
            r_status = requests.get(f"https://graph.facebook.com/v19.0/{id_criacao}?fields=status_code", params={'access_token': META_API_TOKEN_BOCA})
            status = r_status.json().get('status_code')
            print(f"    - Tentativa {i+1}/15: Status do contêiner: {status}")
            if status == 'FINISHED':
                url_publicacao = f"https://graph.facebook.com/v19.0/{INSTAGRAM_ID_BOCA}/media_publish"
                params_publicacao = {'creation_id': id_criacao, 'access_token': META_API_TOKEN_BOCA}
                r_publish = requests.post(url_publicacao, params=params_publicacao, timeout=30)
                r_publish.raise_for_status()
                print("✅ [ETAPA 2/3] Reel publicado no Instagram com sucesso!")
                return True
            time.sleep(10)
        
        print("❌ [ERRO] Contêiner não ficou pronto a tempo.")
        return False
    except Exception as e:
        print(f"❌ [ERRO] Falha na publicação do Reel: {getattr(e, 'response', e)}")
        return False

def publicar_video_facebook(video_url, legenda):
    print("📤 [ETAPA 3/3] Publicando vídeo no Facebook...")
    try:
        url_post_video = f"https://graph.facebook.com/v19.0/{FACEBOOK_PAGE_ID_BOCA}/videos"
        params = {'file_url': video_url, 'description': legenda, 'access_token': META_API_TOKEN_BOCA}
        r = requests.post(url_post_video, params=params, timeout=60)
        r.raise_for_status()
        print("✅ [ETAPA 3/3] Vídeo publicado no Facebook com sucesso!")
        return True
    except Exception as e:
        print(f"❌ [ERRO] Falha ao publicar vídeo no Facebook: {getattr(e, 'response', e)}")
        return False

# ==============================================================================
# BLOCO 4: O MAESTRO (RECEPTOR DO WEBHOOK)
# ==============================================================================
@app.route('/webhook-boca', methods=['POST'])
def webhook_boca():
    print("\n" + "="*50)
    print("🔔 [WEBHOOK BOCA] Webhook recebido!")
    
    try:
        dados_brutos = request.json
        post_info = dados_brutos.get('post', {})
        post_id = post_info.get('ID')
        post_type = post_info.get('post_type')
        post_parent = post_info.get('post_parent')

        if post_type == 'revision' and post_parent:
            print(f"    - Detectada uma REVISÃO. Usando o ID do post principal: {post_parent}")
            post_id = post_parent
        elif not post_id:
             post_id = dados_brutos.get('post_id')

        if not post_id:
            raise ValueError("ID do post final não pôde ser determinado.")

        print(f"✅ [WEBHOOK BOCA] ID do post final para processar: {post_id}")

        url_api_post = f"{WP_URL}/wp-json/wp/v2/posts/{post_id}"
        post_data = requests.get(url_api_post, headers=HEADERS_WP, timeout=15).json()

        titulo_noticia = BeautifulSoup(post_data.get('title', {}).get('rendered', ''), 'html.parser').get_text()
        id_imagem_destaque = post_data.get('featured_media')
        
        url_logo_boca = "https://jornalvozdolitoral.com/wp-content/uploads/2024/04/boca-no-trombone-2-1.png"

        if not id_imagem_destaque or id_imagem_destaque == 0:
            print("❌ [ERRO] Post principal não tem imagem de destaque. Abortando.")
            return jsonify({"status": "erro_sem_imagem"}), 400
        
        media_data = requests.get(f"{WP_URL}/wp-json/wp/v2/media/{id_imagem_destaque}", headers=HEADERS_WP, timeout=15).json()
        url_imagem_destaque = media_data.get('source_url')
        if not url_imagem_destaque:
             print("❌ [ERRO] Não foi possível obter a URL da imagem de destaque. Abortando.")
             return jsonify({"status": "erro_url_imagem"}), 400
            
    except Exception as e:
        print(f"❌ [ERRO CRÍTICO] Falha ao processar dados do webhook: {e}")
        return jsonify({"status": "erro_processamento_wp"}), 500

    print("\n🚀 INICIANDO FLUXO DE PUBLICAÇÃO DE REEL...")
    
    url_do_video_pronto = criar_video_reel(url_imagem_destaque, titulo_noticia, url_logo_boca)
    if not url_do_video_pronto: 
        return jsonify({"status": "erro_criacao_video"}), 500
    
    legenda_boca = (
        f"🗣️ BOCA NO TROMBONE!\n\n"
        f"{titulo_noticia.upper()}\n\n"
        f"A gente foi atrás pra saber tudo sobre essa história! Fica ligado!\n\n"
        f"Fonte: @jornalvozdolitoral\n\n"
        f"#bocanotrombone #noticias #litoralnorte #reportagem #fiquepordentro"
    )
    
    sucesso_ig = publicar_reel_instagram(url_do_video_pronto, legenda_boca)
    sucesso_fb = publicar_video_facebook(url_do_video_pronto, legenda_boca)

    if sucesso_ig or sucesso_fb:
        print("🎉 [SUCESSO] Automação de Reel concluída!")
        return jsonify({"status": "sucesso_publicacao_boca"}), 200
    else:
        print("😭 [FALHA] Nenhuma publicação de Reel foi bem-sucedida.")
        return jsonify({"status": "erro_publicacao_redes_boca"}), 500

# ==============================================================================
# BLOCO 5: INICIALIZAÇÃO
# ==============================================================================
@app.route('/')
def health_check():
    return "Serviço de automação Boca No Trombone v1.5 está no ar.", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
