# ==============================================================================
# BLOCO 1: IMPORTAÇÕES
# ==============================================================================
import os
import io
import requests
import time
from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from base64 import b64encode
import creatomate

# ==============================================================================
# BLOCO 2: CONFIGURAÇÃO INICIAL
# ==============================================================================
load_dotenv()
app = Flask(__name__)

print("🚀 INICIANDO APLICAÇÃO BOCA NO TROMBONE v2.1 (Creatomate - Final)")

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

# --- CONFIGS DA API DO META (BOCA NO TROMBONE) ---
# Garante que estamos usando as variáveis corretas para esta aplicação
BOCA_META_API_TOKEN = os.getenv('BOCA_META_API_TOKEN')
BOCA_INSTAGRAM_ID = os.getenv('BOCA_INSTAGRAM_ID')
BOCA_FACEBOOK_PAGE_ID = os.getenv('BOCA_FACEBOOK_PAGE_ID')
GRAPH_API_VERSION = 'v19.0'

# --- CONFIGS DA API DO CREATOMATE (BOCA NO TROMBONE) ---
BOCA_CREATOMATE_API_KEY = os.getenv('BOCA_CREATOMATE_API_KEY')
BOCA_CREATOMATE_TEMPLATE_ID = os.getenv('BOCA_CREATOMATE_TEMPLATE_ID')

# --- VERIFICAÇÃO DE DIAGNÓSTICO ---
print("-" * 20)
print("VERIFICANDO VARIÁVEIS DE AMBIENTE (BOCA):")
if BOCA_INSTAGRAM_ID:
    print(f"  ✅ Instagram ID (Boca): ...{BOCA_INSTAGRAM_ID[-4:]}")
else:
    print("  ❌ Instagram ID (Boca): NÃO ENCONTRADO")

if BOCA_FACEBOOK_PAGE_ID:
    print(f"  ✅ Facebook Page ID (Boca): ...{BOCA_FACEBOOK_PAGE_ID[-4:]}")
else:
    print("  ❌ Facebook Page ID (Boca): NÃO ENCONTRADO")

if BOCA_META_API_TOKEN:
    print("  ✅ Meta API Token (Boca): Carregado")
else:
    print("  ❌ Meta API Token (Boca): NÃO ENCONTRADO")

if BOCA_CREATOMATE_API_KEY:
    print("  ✅ Creatomate API Key (Boca): Carregada")
else:
    print("  ❌ Creatomate API Key (Boca): NÃO ENCONTRADA")
print("-" * 20)


# ==============================================================================
# BLOCO 3: FUNÇÕES AUXILIARES
# ==============================================================================
def criar_video_com_creatomate(titulo_post, url_imagem_destaque):
    print("🎬 [ETAPA 1/4] Solicitando criação de vídeo ao Creatomate (Boca)...")
    if not all([BOCA_CREATOMATE_API_KEY, BOCA_CREATOMATE_TEMPLATE_ID]):
        print("❌ [ERRO] Chave da API ou ID do Template do Creatomate (Boca) não configurados.")
        return None
    try:
        client = creatomate.Client(BOCA_CREATOMATE_API_KEY)
        modifications = {
            'titulo-noticia': titulo_post,
            'imagem-fundo': url_imagem_destaque,
        }
        renders = client.render({'template_id': BOCA_CREATOMATE_TEMPLATE_ID, 'modifications': modifications})
        print("    - Renderização iniciada. Aguardando finalização...")
        video_renderizado = renders[0]
        print(f"✅ [ETAPA 1/4] Vídeo (Boca) criado com sucesso! URL: {video_renderizado.url}")
        return video_renderizado.url
    except Exception as e:
        print(f"❌ [ERRO] Falha crítica na comunicação com o Creatomate: {e}")
        return None

def upload_para_wordpress(url_video, nome_arquivo):
    print(f"⬆️  [ETAPA 2/4] Fazendo upload do vídeo (Boca) para o WordPress...")
    try:
        print("    - Baixando vídeo do Creatomate...")
        response_video = requests.get(url_video, stream=True, timeout=60)
        response_video.raise_for_status()
        video_bytes = response_video.content
        
        print("    - Enviando para o WordPress...")
        url_wp_media = f"{WP_URL}/wp-json/wp/v2/media"
        headers_upload = HEADERS_WP.copy()
        headers_upload['Content-Disposition'] = f'attachment; filename={nome_arquivo}'
        headers_upload['Content-Type'] = 'video/mp4'
        response_wp = requests.post(url_wp_media, headers=headers_upload, data=video_bytes, timeout=60)
        response_wp.raise_for_status()
        link_video_publico = response_wp.json()['source_url']
        print(f"✅ [ETAPA 2/4] Vídeo (Boca) salvo no WordPress!")
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
        params_container = {'media_type': 'REELS', 'video_url': url_video, 'caption': legenda, 'access_token': BOCA_META_API_TOKEN}
        r_container = requests.post(url_container, params=params_container, timeout=30); r_container.raise_for_status()
        id_criacao = r_container.json()['id']
        
        print("    - [Passo 2/3] Verificando status do upload...")
        for _ in range(20):
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
        dados_brutos = request.json
        post_info = dados_brutos.get('post', {})
        post_id = post_info.get('ID')
        post_type = post_info.get('post_type')
        post_parent = post_info.get('post_parent')

        if post_type == 'revision' and post_parent: post_id = post_parent
        elif not post_id: post_id = dados_brutos.get('post_id')
        if not post_id: raise ValueError("ID do post não encontrado.")

        print(f"✅ [WEBHOOK BOCA] ID do post extraído: {post_id}")
        
        url_api_post = f"{WP_URL}/wp-json/wp/v2/posts/{post_id}"
        response_post = requests.get(url_api_post, headers=HEADERS_WP, timeout=15); response_post.raise_for_status()
        post_data = response_post.json()

        titulo_noticia = BeautifulSoup(post_data.get('title', {}).get('rendered', ''), 'html.parser').get_text()
        resumo_noticia = BeautifulSoup(post_data.get('excerpt', {}).get('rendered', ''), 'html.parser').get_text(strip=True)
        id_imagem_destaque = post_data.get('featured_media')

        if not id_imagem_destaque or id_imagem_destaque == 0:
            return jsonify({"status": "ignorado_sem_imagem"}), 200
            
        url_api_media = f"{WP_URL}/wp-json/wp/v2/media/{id_imagem_destaque}"
        response_media = requests.get(url_api_media, headers=HEADERS_WP, timeout=15); response_media.raise_for_status()
        url_imagem_destaque = response_media.json().get('source_url')
            
    except Exception as e:
        print(f"❌ [ERRO CRÍTICO BOCA] Falha ao processar dados do webhook: {e}")
        return jsonify({"status": "erro_processamento_wp_boca"}), 500

    print("\n🚀 INICIANDO FLUXO DE PUBLICAÇÃO (BOCA via Creatomate)...")
    
    url_video_creatomate = criar_video_com_creatomate(titulo_noticia, url_imagem_destaque)
    if not url_video_creatomate: return jsonify({"status": "erro_criacao_video_creatomate"}), 500
    
    nome_do_arquivo = f"reel_boca_{post_id}.mp4"
    link_wp_video = upload_para_wordpress(url_video_creatomate, nome_do_arquivo)
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
    return "Serviço de automação Boca No Trombone v2.1 (Creatomate) está no ar.", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10001))
    app.run(host='0.0.0.0', port=port)
