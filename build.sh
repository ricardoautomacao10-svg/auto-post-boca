#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Iniciando processo de build..."

# 1. Instalação do Google Chrome e suas dependências
echo "Instalando Google Chrome..."
apt-get update && apt-get install -y wget gnupg
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome-keyring.gpg
sh -c 'echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list'
apt-get update
apt-get install -y google-chrome-stable
echo "Google Chrome instalado com sucesso."

# 2. Instalação do FFmpeg (se ainda não estiver instalado por outro método)
echo "Instalando FFmpeg..."
apt-get install -y ffmpeg
echo "FFmpeg instalado com sucesso."

# 3. Instalação das dependências Python
echo "Instalando pacotes Python..."
pip install -r requirements.txt
echo "Build finalizado."
