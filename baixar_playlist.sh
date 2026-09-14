#!/bin/bash

# ==============================================================================
# Script de Download de Playlists do YouTube (Áudio MP3 - Alta Qualidade)
# ==============================================================================

# 1. DIRETÓRIOS PADRÃO E DE TESTE
DEFAULT_DIR="$HOME/Documents/Music/Downloads"
TEST_DIR="$HOME/Documents/Music/Test/Downloads"

# Diretório inicial (padrão)
DOWNLOAD_DIR="$DEFAULT_DIR"

# 2. TRATAMENTO DE ARGUMENTOS/FLAGS
PLAYLIST_URL=""

for arg in "$@"; do
    case $arg in
        --test|-t)
            DOWNLOAD_DIR="$TEST_DIR"
            shift
            ;;
        *)
            # Assume que o argumento sem flag é a URL
            if [ -z "$PLAYLIST_URL" ]; then
                PLAYLIST_URL="$arg"
            fi
            ;;
    esac
done

# Verifica se a URL foi fornecida
if [ -z "$PLAYLIST_URL" ]; then
    echo "Erro: Nenhuma URL fornecida!"
    echo "Uso: $0 [--test] <URL_DA_PLAYLIST>"
    exit 1
fi

# Cria a pasta de destino caso ela não exista
mkdir -p "$DOWNLOAD_DIR"

# 3. VERIFICAÇÃO DE DEPENDÊNCIAS
if ! command -v yt-dlp &> /dev/null; then
    echo "Erro: yt-dlp não está instalado. Instale usando: brew install yt-dlp"
    exit 1
fi

if ! command -v ffmpeg &> /dev/null; then
    echo "Erro: ffmpeg não está instalado. Instale usando: brew install ffmpeg"
    exit 1
fi

# 4. EXECUÇÃO DO DOWNLOAD
echo "Iniciando o download..."
echo "Diretório de destino: $DOWNLOAD_DIR"
echo "------------------------------------------------------------"

yt-dlp \
  -x \
  --audio-format mp3 \
  --audio-quality 0 \
  --add-metadata \
  --embed-thumbnail \
  --extractor-args "youtube:player_client=mweb,web" \
  -P "$DOWNLOAD_DIR" \
  "$PLAYLIST_URL"

echo "------------------------------------------------------------"
echo "Download concluído com sucesso!"
