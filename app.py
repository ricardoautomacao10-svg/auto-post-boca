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

# ==============================================================================
# BLOCO 2: CONFIGURAÇÃO INICIAL
# ==============================================================================
load_dotenv()
app = Flask(__name__)

print("🚀 INICIANDO APLICAÇÃO BOCA NO TROMBONE v8.0 (Final)")

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

# --- CONFIG do Creatomate (API de Vídeo) ---
CREATOMATE_API_KEY = os.getenv('CREATOMATE_API_KEY')
CREATOMATE_TEMPLATE_ID = os.getenv('CREATOMATE_TEMPLATE_ID')
if CREATOMATE_API_KEY and CREATOMATE_TEMPLATE_ID:
    print("✅ [CONFIG] Chave e Template ID do Creatomate carregados.")
else:
    print("❌ [ERRO DE CONFIG] Faltando a chave ou o Template ID do Creatomate.")

# ==============================================================================
# BLOCO 3: FUNÇÕES DE PUBLICAÇÃO
# ==============================================================================

def criar_video_reel(url_imagem_noticia, titulo_noticia):
    print("🎬 [ETAPA 1/3] Iniciando criação do vídeo Reel com Creatomate...")
    if not CREATOMATE_API_KEY:
        return None

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CREATOMATE_API_KEY}"
    }
    data = {
        "template_id": CREATOMATE_TEMPLATE_ID,
        "modifications": {
            'Background-1.source': url_imagem_noticia,
            'titulo-noticia.text': titulo_noticia.upper()
        }
    }

    try:
        print("    - Enviando requisição para a API de vídeo...")
        response = requests.post("https://api.creatomate.com/v1/renders", json=data, headers=headers)
        response.raise_for_status()
        render_info_list = response.json()
        
        if not render_info_list:
            print("❌ [ERRO] API do Creatomate não retornou informações de renderização.")
            return None
        
        render_info = render_info_list[0]
        render_id = render_info.get('id')
        
        print(f"    - Renderização iniciada com ID: {render_id}. Aguardando...")
        
        for i in range(20):
            time.sleep(10)
            status_response = requests.get(f"https://api.creatomate.com/v1/renders?_id={render_id}", headers=headers)
            status_response.raise_for_status()
            
            render_info_list = status_response.json()
            if not render_info_list:
                continue

            render_info = render_info_list[0]
            status = render_info.get('status')
            print(f"    - Tentativa {i+1}/20: Status atual: {status}")

            if status == 'succeeded':
                video_url = render_info.get('url')
                print(f"✅ [ETAPA 1/3] Vídeo criado com sucesso! URL: {video_url}")
                return video_url
            elif status == 'failed':
                print(f"❌ [ERRO] A renderização do vídeo falhou: {render_info.get('status_message')}")
                return None

        print("❌ [ERRO] Tempo de espera para renderização do vídeo excedido.")
        return None

    except Exception as e:
        print(f"❌ [ERRO] Falha na comunicação com a API de vídeo Creatomate. Erro: {e}")
        if hasattr(e, 'response'): print(f"    - Resposta da API: {e.response.text}")
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
            time.sleep(10)
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

        if not id_imagem_destaque or id_imagem_destaque == 0:
            return jsonify({"status": "erro_sem_imagem"}), 400
        
        media_data = requests.get(f"{WP_URL}/wp-json/wp/v2/media/{id_imagem_destaque}", headers=HEADERS_WP, timeout=15).json()
        url_imagem_destaque = media_data.get('source_url')
        if not url_imagem_destaque:
             return jsonify({"status": "erro_url_imagem"}), 400
            
    except Exception as e:
        print(f"❌ [ERRO CRÍTICO] Falha ao processar dados do webhook: {e}")
        return jsonify({"status": "erro_processamento_wp"}), 500

    print("\n🚀 INICIANDO FLUXO DE PUBLICAÇÃO DE REEL...")
    
    url_do_video_pronto = criar_video_reel(url_imagem_destaque, titulo_noticia)
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
    return "Serviço de automação Boca No Trombone v8.0 (Final) está no ar.", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
