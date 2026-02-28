"""
API REST para conversão de MP4 para MP3
"""
import os
import subprocess
import uuid
from pathlib import Path

from flask import Flask, request, jsonify, send_file, render_template

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024 * 1024  # 2 GB max

UPLOAD_FOLDER = Path(__file__).parent / "uploads"
OUTPUT_FOLDER = Path(__file__).parent / "output"
UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)


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
                download_name=f"{nome_base}.mp3",
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
