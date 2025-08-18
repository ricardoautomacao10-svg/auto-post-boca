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

# NOVA IMPORTAÇÃO para a API de Vídeo (Creatomate)
import creatomate

# ==============================================================================
# BLOCO 2: CONFIGURAÇÃO INICIAL
# ==============================================================================
load_dotenv()
app = Flask(__name__)

print("🚀 INICIANDO APLICAÇÃO BOCA NO TROMBONE v2.0 (Creatomate)")

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

# --- NOVA CONFIG do Creatomate (API de Vídeo) ---
CREATOMATE_API_KEY = os.getenv('CREATOMATE_API_KEY')
CREATOMATE_TEMPLATE_ID = os.getenv('CREATOMATE_TEMPLATE_ID')
if CREATOMATE_API_KEY and CREATOMATE_TEMPLATE_ID:
    print("✅ [CONFIG] Chave e Template ID do Creatomate carregados.")
    creatomate.Client.api_key = CREATOMATE_API_KEY
else:
    print("❌ [ERRO DE CONFIG] Faltando a chave ou o Template ID do Creatomate.")

# ==============================================================================
# BLOCO 3: FUNÇÕES DE PUBLICAÇÃO
# ==============================================================================

def criar_video_reel(url_imagem_noticia, titulo_noticia):
    print("🎬 [ETAPA 1/3] Iniciando criação do vídeo Reel com Creatomate...")
    if not CREATOMATE_API_KEY:
        return None

    try:
        print("    - Enviando requisição para a API de vídeo...")
        source = creatomate.Source(
            output_format='mp4',
            # Modificações no seu template
            modifications={
                'imagem-noticia': url_imagem_noticia,
                'titulo-noticia': titulo_noticia.upper()
            }
        )
        
        renders = creatomate.render({
            'template_id': CREATOMATE_TEMPLATE_ID,
            'source': source,
        })

        print(f"    - Renderização iniciada. Aguardando...")
        
        # Espera o vídeo ficar pronto (pode demorar)
        render_result = renders[0].wait()

        if render_result.status == 'succeeded':
            video_url = render_result.url
            print(f"✅ [ETAPA 1/3] Vídeo criado com sucesso! URL: {video_url}")
            return video_url
        else:
            print(f"❌ [ERRO] A renderização do vídeo falhou: {render_result.status_message}")
            return None

    except Exception as e:
        print(f"❌ [ERRO] Falha na comunicação com a API de vídeo Creatomate: {e}")
        return None

# ... (O resto do código, como as funções publicar_reel_instagram e publicar_video_facebook, permanece EXATAMENTE O MESMO) ...
# ... (A função webhook_boca também permanece a mesma, apenas a chamada a criar_video_reel não precisa mais do logo) ...

# ==============================================================================
# BLOCO 4: O MAESTRO (RECEPTOR DO WEBHOOK)
# ==============================================================================
@app.route('/webhook-boca', methods=['POST'])
def webhook_boca():
    print("\n" + "="*50)
    print("🔔 [WEBHOOK BOCA] Webhook recebido!")
    
    try:
        # ... (código de extração de dados do WordPress - sem alterações) ...
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
    
    # A chamada agora é mais simples
    url_do_video_pronto = criar_video_reel(url_imagem_destaque, titulo_noticia)
    if not url_do_video_pronto: 
        return jsonify({"status": "erro_criacao_video"}), 500
    
    # ... (resto do código para criar legenda e publicar - sem alterações) ...
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

# ... (O resto do código de inicialização é o mesmo) ...
@app.route('/')
def health_check():
    return "Serviço de automação Boca No Trombone v2.0 (Creatomate) está no ar.", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
