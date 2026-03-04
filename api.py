"""
API REST para conversão de MP4 para MP3
"""
import os
import re
import subprocess
import uuid
from datetime import date
from pathlib import Path

from flask import Flask, request, jsonify, send_file, render_template

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024 * 1024  # 2 GB max

UPLOAD_FOLDER = Path(__file__).parent / "uploads"
OUTPUT_FOLDER = Path(__file__).parent / "output"
UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)

# Listas para o front (mesmas da GUI)
MATERIAS = [
    "ALIANÇA DE SANGUE",
    "AUTORIDADE DO CRENTE",
    "AS MANIFESTAÇÕES DO ESPÍRITO",
    "CARÁTER DE DEUS",
    "COMO SER GUIADO PELO ESPÍRITO",
    "CRISTO, AQUELE QUE CURA",
    "DOUTRINAS BÁSICAS DA BÍBLIA",
    "ESCATOLOGIA",
    "EVANGELISMO",
    "FAMÍLIA CRISTÃ",
    "FRUTO DO ESPÍRITO",
    "FUNDAMENTOS DA FÉ",
    "GÁLATAS",
    "HISTÓRIA DA IGREJA",
    "JUSTIÇA DE DEUS",
    "MINISTÉRIO PRÁTICO",
    "MINISTRANDO A PALAVRA",
    "O LIVRO DE ATOS",
    "ORAÇÃO QUE PREVALECE",
    "REALIDADES DA NOVA CRIAÇÃO",
    "SUBMISSÃO E AUTORIDADE",
    "VIDA DE LOUVOR",
    "VIDA DE PROSPERIDADE",
    "UNÇÃO",
]
AULAS = [f"Aula {i}" for i in range(1, 8)]  # Aula 1 até Aula 7
PARTES = ["Parte 1", "Parte 2"]


def _sanitizar_nome(texto: str) -> str:
    if not texto or not str(texto).strip():
        return "arquivo"
    texto = re.sub(r"[^\w\s\-áéíóúàèìòùãõâêîôûç]", "", str(texto).strip(), flags=re.IGNORECASE)
    texto = re.sub(r"[\s]+", "_", texto)
    return texto or "arquivo"


def _nome_download_mp3(materia: str, aula: str, parte: str) -> str:
    """Nome final: materia_aula_parte_dataAtual.mp3"""
    data_atual = date.today().isoformat()
    return f"{_sanitizar_nome(materia)}_{_sanitizar_nome(aula)}_{_sanitizar_nome(parte)}_{data_atual}.mp3"


def converter_mp4_para_mp3(arquivo_mp4: str, arquivo_mp3: str):
    """Converte arquivo MP4 para MP3 usando FFmpeg."""
    if not os.path.isfile(arquivo_mp4):
        return False

    comando = [
        "ffmpeg",
        "-i", arquivo_mp4,
        "-vn",
        "-ab", "192k",
        "-ar", "44100",
        "-y",
        arquivo_mp3
    ]

    try:
        subprocess.run(comando, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        return None


@app.route("/")
def index():
    """Página principal com interface HTML."""
    return render_template("index.html")


@app.route("/api/health", methods=["GET"])
def health():
    """Verifica se a API está online."""
    return jsonify({"status": "ok", "servico": "converter-mp4-mp3"})


@app.route("/api/convert", methods=["POST"])
def convert():
    """
    Converte MP4 para MP3.
    Aceita: multipart/form-data com arquivo 'file' (MP4)
    Retorna: arquivo MP3 ou JSON com erro
    """
    if "file" not in request.files:
        return jsonify({"erro": "Nenhum arquivo enviado"}), 400

    arquivo = request.files["file"]
    if arquivo.filename == "":
        return jsonify({"erro": "Nenhum arquivo selecionado"}), 400

    if not arquivo.filename.lower().endswith(".mp4"):
        return jsonify({"erro": "Apenas arquivos MP4 são aceitos"}), 400

    materia = request.form.get("materia", "").strip()
    aula = request.form.get("aula", "").strip()
    parte = request.form.get("parte", "").strip()
    if materia and aula and parte:
        nome_download = _nome_download_mp3(materia, aula, parte)
    else:
        nome_download = f"{Path(arquivo.filename).stem}.mp3"

    # Salvar upload
    id_unico = str(uuid.uuid4())[:8]
    nome_base = Path(arquivo.filename).stem
    arquivo_mp4 = UPLOAD_FOLDER / f"{nome_base}_{id_unico}.mp4"
    arquivo_mp3 = OUTPUT_FOLDER / f"{nome_base}_{id_unico}.mp3"

    try:
        arquivo.save(arquivo_mp4)
        resultado = converter_mp4_para_mp3(str(arquivo_mp4), str(arquivo_mp3))

        if resultado is True:
            resp = send_file(
                arquivo_mp3,
                as_attachment=True,
                download_name=nome_download,
                mimetype="audio/mpeg"
            )

            @resp.call_on_close
            def cleanup():
                arquivo_mp4.unlink(missing_ok=True)
                arquivo_mp3.unlink(missing_ok=True)

            return resp
        elif resultado is False:
            return jsonify({"erro": "Falha na conversão. Verifique se o arquivo é válido."}), 500
        else:
            return jsonify({"erro": "FFmpeg não encontrado. Instale o FFmpeg no servidor."}), 503
    except Exception:
        arquivo_mp4.unlink(missing_ok=True)
        arquivo_mp3.unlink(missing_ok=True)
        raise


@app.route("/api/convert/json", methods=["POST"])
def convert_json():
    """
    Converte MP4 para MP3 e retorna resposta em JSON.
    Útil para integração com frontends que precisam de status.
    """
    if "file" not in request.files:
        return jsonify({"sucesso": False, "erro": "Nenhum arquivo enviado"}), 400

    arquivo = request.files["file"]
    if arquivo.filename == "":
        return jsonify({"sucesso": False, "erro": "Nenhum arquivo selecionado"}), 400

    if not arquivo.filename.lower().endswith(".mp4"):
        return jsonify({"sucesso": False, "erro": "Apenas arquivos MP4 são aceitos"}), 400

    id_unico = str(uuid.uuid4())[:8]
    nome_base = Path(arquivo.filename).stem
    arquivo_mp4 = UPLOAD_FOLDER / f"{nome_base}_{id_unico}.mp4"
    arquivo_mp3 = OUTPUT_FOLDER / f"{nome_base}_{id_unico}.mp3"

    try:
        arquivo.save(arquivo_mp4)
        resultado = converter_mp4_para_mp3(str(arquivo_mp4), str(arquivo_mp3))

        if resultado is True:
            return jsonify({
                "sucesso": True,
                "mensagem": "Conversão concluída",
                "download_url": f"/api/download/{nome_base}_{id_unico}.mp3"
            })
        elif resultado is False:
            return jsonify({"sucesso": False, "erro": "Falha na conversão"}), 500
        else:
            return jsonify({"sucesso": False, "erro": "FFmpeg não encontrado"}), 503
    finally:
        if arquivo_mp4.exists():
            arquivo_mp4.unlink()


@app.route("/api/download/<nome_arquivo>", methods=["GET"])
def download(nome_arquivo):
    """Download de arquivo MP3 convertido (por ID)."""
    caminho = OUTPUT_FOLDER / nome_arquivo
    if not caminho.exists():
        return jsonify({"erro": "Arquivo não encontrado"}), 404
    resp = send_file(caminho, as_attachment=True, download_name=nome_arquivo)

    @resp.call_on_close
    def cleanup():
        caminho.unlink(missing_ok=True)

    return resp


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true")
