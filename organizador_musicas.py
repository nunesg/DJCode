import os
# Silencia o aviso de deprecation do Tk no macOS antes de importar o tkinter
os.environ["TK_SILENCE_DEPRECATION"] = "1"
import tkinter as tk

from tkinter import filedialog
import re
import json
import time
from google import genai
from google.genai import types
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3

# ==========================================
# CONFIGURAÇÕES
# ==========================================
TAMANHO_LOTE = 25  # Quantidade de músicas enviadas por lote para a API
EXTENSOES_SUPORTADAS = ('.mp3', '.MP3')
HISTORICO_FILE = "historico_processados.json"

# Defina sua API Key diretamente aqui ou via variável de ambiente GEMINI_API_KEY
# Exemplo: client = genai.Client(api_key="SUA_CHAVE_AQUI")
client = genai.Client()

SYSTEM_PROMPT = """
Você é um especialista em metadados de áudio e curadoria de música brasileira, com foco em forró (pé de serra, universitário, eletrônico), brasilidades, MPB e ritmos regionais.

Sua tarefa é analisar uma lista de arquivos de áudio. Para cada item, você receberá o nome original do arquivo E as tags de metadados existentes (se houver).

SUA MISSÃO E REGRAS:
1. IDENTIFICAÇÃO DO ARTISTA:
   - Identifique o artista principal a partir do nome do arquivo ou tags.
   - CASO O NOME CONTEINHA APENAS O TÍTULO DA MÚSICA (ex: "Rojão de Brasília"):
     Músicas clássicas do forró/brasilidades possuem associações fortíssimas com artistas ou compositores icônicos.
     Você deve inferir o artista provável através do contexto cultural, alem das informacoes das tags ja definidas.
     Crie mentalmente uma lista de opções com taxas de probabilidade (0% a 100%).
     - Se a opção mais provável tiver probabilidade MAIOR OU IGUAL A 60%, atribua esse artista ao campo "artist".
     - Se nenhuma opção atingir 60% ou houver incerteza/ambiguidade relevante, atribua ESTRITAMENTE "Unknown" ao campo "artist".

2. PARTICIPAÇÕES E DJS (feat. / part.):
   - O campo "artist" deve conter APENAS o artista principal.
   - Se houver participações especiais, vocalistas convidados ou DJs (ex: 'feat.', 'part.', 'ft.', 'DJ X'), inclua essa informação no TÍTULO entre parênteses.
     Exemplo: "Asa Branca (feat. MC Blabla)"
     Exemplo: "Procurando Tu (part. DJ Fulano)"

3. LIMPEZA DE TÍTULO:
   - Limpe ruídos de downloads/YouTube (ex: '(Ao Vivo)', '[Official Video]', '128kbps', 'HQ', 'Áudio Oficial', etc.).
   - Aplique Title Case adequado em português (ex: 'Luiz Gonzaga', 'Rojão de Brasília').
   - Mantenha o "title" sempre limpo, mesmo se o artista for "Unknown".

4. FORMATO DE SAÍDA:
   - Retorne ESTRITAMENTE um array JSON com os objetos no formato:
     [{"original": "nome_do_arquivo.mp3", "artist": "Nome do Artista", "title": "Nome da Musica"}]
"""

RESPONSE_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "original": {"type": "STRING"},
            "artist": {"type": "STRING"},
            "title": {"type": "STRING"}
        },
        "required": ["original", "artist", "title"]
    }
}


# ==========================================
# GESTÃO DE HISTÓRICO LOCAL
# ==========================================
def carregar_historico(pasta_raiz):
    """Carrega o conjunto de arquivos já processados no passado."""
    caminho_historico = os.path.join(pasta_raiz, HISTORICO_FILE)
    if os.path.exists(caminho_historico):
        try:
            with open(caminho_historico, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception as e:
            print(f"Aviso: Não foi possível ler o histórico ({e}). Criando um novo.")
    return set()


def salvar_historico(pasta_raiz, historico_set):
    """Salva o histórico atualizado de arquivos processados."""
    caminho_historico = os.path.join(pasta_raiz, HISTORICO_FILE)
    try:
        with open(caminho_historico, "w", encoding="utf-8") as f:
            json.dump(list(historico_set), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Erro ao salvar arquivo de histórico: {e}")


# ==========================================
# MANIPULAÇÃO DE METADADOS E ARQUIVOS
# ==========================================
def ler_tags_existentes(caminho_arquivo):
    """Lê as tags ID3 atuais do arquivo para passar como contexto extra para a IA."""
    tags = {}
    try:
        audio = MP3(caminho_arquivo, ID3=EasyID3)
        tags["artist"] = audio.get("artist", [""])[0]
        tags["title"] = audio.get("title", [""])[0]
        tags["album"] = audio.get("album", [""])[0]
        tags["description"] = audio.get("description", [""])[0]
    except Exception:
        tags = {"artist": "", "title": "", "album": "", "description": ""}
    return tags


def atualizar_tags_id3(caminho_arquivo, artista, titulo):
    """Escreve os metadados finais de Artista e Título no MP3."""
    try:
        audio = MP3(caminho_arquivo, ID3=EasyID3)
    except Exception:
        audio = MP3(caminho_arquivo)
        audio.add_tags()
        audio = MP3(caminho_arquivo, ID3=EasyID3)

    audio['artist'] = artista
    audio['title'] = titulo
    audio.save()


def sanitizar_nome_arquivo(nome):
    """Remove caracteres inválidos para o sistema operacional."""
    return re.sub(r'[\\/*?:"<>|]', "", nome).strip()


def renomear_arquivo_local(caminho_original, artista, titulo):
    """Renomeia o arquivo mantendo a subpasta de origem intacta."""
    pasta_atual = os.path.dirname(caminho_original)
    _, extensao = os.path.splitext(caminho_original)

    novo_nome_base = f"{artista} - {titulo}{extensao}"
    novo_nome_limpo = sanitizar_nome_arquivo(novo_nome_base)
    novo_caminho = os.path.join(pasta_atual, novo_nome_limpo)

    # Evita colisões de arquivos com o mesmo nome dentro da mesma subpasta
    contador = 1
    while os.path.exists(novo_caminho) and novo_caminho != caminho_original:
        nome_sem_ext, ext = os.path.splitext(novo_nome_limpo)
        novo_caminho = os.path.join(pasta_atual, f"{nome_sem_ext} ({contador}){ext}")
        contador += 1

    if caminho_original != novo_caminho:
        os.rename(caminho_original, novo_caminho)
        return novo_caminho, os.path.basename(novo_caminho)
    return caminho_original, os.path.basename(caminho_original)


# ==========================================
# REQUISIÇÕES GEMINI API (COM TRATAMENTO DE COTA)
# ==========================================
def processar_lote_ia(lote_dados, max_tentativas=4):
    """Envia um lote para o Gemini 2.5 Flash tratando erros de cota (429 / Rate Limit)."""
    prompt_usuario = "Analise os arquivos e metadados a seguir para extrair o artista e título corretos:\n"
    prompt_usuario += json.dumps(lote_dados, ensure_ascii=False, indent=2)

    for tentativa in range(max_tentativas):
        try:
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt_usuario,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=RESPONSE_SCHEMA,
                    temperature=0.1
                )
            )
            return json.loads(response.text)
        except Exception as e:
            erro_str = str(e)
            if "429" in erro_str or "RESOURCE_EXHAUSTED" in erro_str or "Quota" in erro_str:
                tempo_espera = (tentativa + 1) * 12  # Backoff progressivo: 12s, 24s, 36s...
                print(f"   [Cota da API Atingida] Aguardando {tempo_espera}s para tentar novamente...")
                time.sleep(tempo_espera)
            else:
                print(f"Erro ao processar lote na API do Gemini: {e}")
                break

    return []


# ==========================================
# ORQUESTRAÇÃO DA BIBLIOTECA
# ==========================================
def processar_biblioteca(pasta_raiz):
    """Varre a pasta de forma recursiva e atualiza os arquivos localmente."""

    if not os.path.exists(pasta_raiz):
        print(f"[ERRO CRÍTICO] A pasta '{pasta_raiz}' não foi encontrada.")
        return

    print(f"Iniciando varredura recursiva em: {pasta_raiz}\n")

    historico = carregar_historico(pasta_raiz)

    # 1. Varredura e filtragem de arquivos com base no histórico
    arquivos_para_processar = []
    pulas = 0

    for raiz, _, arquivos in os.walk(pasta_raiz):
        for arquivo in arquivos:
            if arquivo == HISTORICO_FILE:
                continue

            if arquivo.lower().endswith(EXTENSOES_SUPORTADAS):
                caminho_completo = os.path.join(raiz, arquivo)

                # Se já estiver registrado no histórico, ignora
                if arquivo in historico:
                    pulas += 1
                    continue

                tags_atuais = ler_tags_existentes(caminho_completo)
                arquivos_para_processar.append({
                    "original": arquivo,
                    "caminho_completo": caminho_completo,
                    "existing_tags": tags_atuais
                })

    total = len(arquivos_para_processar)
    print(f"Músicas já processadas anteriormente (ignoradas): {pulas}")
    print(f"Novas músicas a processar: {total}\n")

    if total == 0:
        print("Nenhuma nova música para processar!")
        return

    total_lotes = ((total - 1) // TAMANHO_LOTE) + 1

    # 2. Processamento em Lotes (Batches)
    for i in range(0, total, TAMANHO_LOTE):
        fatia_lote = arquivos_para_processar[i:i + TAMANHO_LOTE]
        numero_lote = (i // TAMANHO_LOTE) + 1

        print(f"--> Processando lote {numero_lote} de {total_lotes} ({len(fatia_lote)} músicas)...")

        payload_ia = [
            {
                "original": item["original"],
                "existing_tags": item["existing_tags"]
            }
            for item in fatia_lote
        ]

        mapa_caminhos = {item["original"]: item["caminho_completo"] for item in fatia_lote}

        resultados_json = processar_lote_ia(payload_ia)

        # 3. Atualiza as tags ID3, renomeia o arquivo e grava no histórico
        for item in resultados_json:
            nome_original = item.get("original")
            artista = item.get("artist", "Unknown").strip()
            titulo = item.get("title", "Desconhecido").strip()

            caminho_original = mapa_caminhos.get(nome_original)

            if caminho_original and os.path.exists(caminho_original):
                try:
                    # Passo A: Atualiza Tag ID3 interna
                    atualizar_tags_id3(caminho_original, artista, titulo)

                    # Passo B: Renomeia mantendo na subpasta original
                    novo_caminho, novo_nome = renomear_arquivo_local(caminho_original, artista, titulo)

                    # Passo C: Adiciona tanto o nome antigo quanto o novo ao histórico
                    historico.add(nome_original)
                    historico.add(novo_nome)

                    print(f" [OK] {nome_original}\n   └─► {novo_nome}")
                except Exception as e:
                    print(f" [ERRO] Falha ao processar {nome_original}: {e}")

        # Salva o arquivo JSON de histórico após cada lote concluído
        salvar_historico(pasta_raiz, historico)

        # Pausa de 3 segundos entre lotes para evitar estourar limites de requisição por minuto
        time.sleep(3)

    print("\nProcessamento concluído com sucesso!")

def selecionar_pasta():
    # Printa instrução clara no terminal ANTES de invocar a janela
    print("\n[AÇÃO NECESSÁRIA] Uma janela de seleção de pasta foi aberta.")
    print("Caso não veja a janela na tela, confira o ícone do Python no seu dock/barra de tarefas.\n")
    
    root = tk.Tk()
    root.withdraw()  # Esconde a janela principal em branco
    
    # Força a janela do Tkinter a ir para o topo absoluto das janelas
    root.attributes('-topmost', True)
    root.update()
    
    # Truque específico para macOS/Linux trazer o aplicativo Python para o primeiro plano
    try:
        root.lift()
        root.focus_force()
    except Exception:
        pass

    caminho_pasta = filedialog.askdirectory(
        title="Selecione a pasta com sua biblioteca de músicas"
    )
    
    root.destroy()  # Destrói a instância oculta do Tkinter após a escolha
    return caminho_pasta

# ==========================================
# EXECUÇÃO DO SCRIPT
# ==========================================
if __name__ == "__main__":
    pasta_selecionada = selecionar_pasta()
    
    if pasta_selecionada:
        print(f"Pasta selecionada: {pasta_selecionada}")
        processar_biblioteca(pasta_selecionada)
    else:
        print("Nenhuma pasta foi selecionada. Operação cancelada.")
