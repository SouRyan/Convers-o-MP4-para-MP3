import os
import subprocess

def converter_mp4_para_mp3(arquivo_mp4, arquivo_mp3):
    # Verifica se o arquivo existe
    if not os.path.isfile(arquivo_mp4):
        print("Arquivo não encontrado!")
        return
    
    # Comando FFmpeg
    comando = [
        "ffmpeg",
        "-i", arquivo_mp4,
        "-vn",                 # Remove vídeo
        "-ab", "192k",         # Bitrate do áudio
        "-ar", "44100",        # Frequência
        "-y",                  # Sobrescreve se existir
        arquivo_mp3
    ]
    
    try:
        subprocess.run(comando, check=True)
        print("Conversão concluída com sucesso!")
    except subprocess.CalledProcessError:
        print("Erro na conversão.")

# Exemplo de uso
converter_mp4_para_mp3("video.mp4", "audio.mp3")