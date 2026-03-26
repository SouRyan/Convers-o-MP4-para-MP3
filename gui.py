"""
Interface visual para conversão de MP4 para MP3 e compressão de MP3
"""
import logging
import os
import re
import shutil
import subprocess
import tkinter as tk
from datetime import datetime
from tkinter import ttk, filedialog, messagebox

# Listas para o usuário selecionar (conforme a igreja)
MATERIAS = [
    "ALIANCA DE SANGUE",
    "AUTORIDADE DO CRENTE",
    "AS MANIFESTACOES DO ESPIRITO",
    "CARATER DE DEUS",
    "COMO SER GUIADO PELO ESPIRITO",
    "CRISTO, AQUELE QUE CURA",
    "DOUTRINAS BASICAS DA BIBLIA",
    "ESCATOLOGIA",
    "EVANGELISMO",
    "FAMILIA CRISTA",
    "FRUTO DO ESPIRITO",
    "FUNDAMENTOS DA FE",
    "GALATAS",
    "HISTORIA DA IGREJA",
    "JUSTICA DE DEUS",
    "MINISTERIO PRATICO",
    "MINISTRANDO A PALAVRA",
    "O LIVRO DE ATOS",
    "ORACAO QUE PREVALECE",
    "REALIDADES DA NOVA CRIACAO",
    "SUBMISSAO E AUTORIDADE",
    "VIDA DE LOUVOR",
    "VIDA DE PROSPERIDADE",
    "UNCAO",
]

AULAS = [f"Aula {i}" for i in range(1, 8)]  # Aula 1 até Aula 7

PARTES = ["Parte 1", "Parte 2"]

# Compressão de MP3 (limite da plataforma de upload)
MAX_MP3_INPUT_BYTES = 95 * 1024 * 1024
MAX_MP3_OUTPUT_BYTES = 45 * 1024 * 1024
MP3_BITRATE_MIN_KBPS = 32
MP3_BITRATE_MAX_KBPS = 320

_compress_logger = None


def _log_compressao():
    """Logger só para compressão MP3 (saída no console ao rodar com python gui.py)."""
    global _compress_logger
    if _compress_logger is not None:
        return _compress_logger
    log = logging.getLogger("converter.compressao")
    log.setLevel(logging.DEBUG)
    log.propagate = False
    if not log.handlers:
        h = logging.StreamHandler()
        h.setFormatter(
            logging.Formatter("%(asctime)s [compressão] %(levelname)s %(message)s", datefmt="%H:%M:%S")
        )
        log.addHandler(h)
    _compress_logger = log
    return log


def _trace_write(var, callback):
    """Compatível com Python 3.7 (trace) e 3.8+ (trace_add)."""
    try:
        var.trace_add("write", callback)
    except AttributeError:
        var.trace("w", callback)


def _sanitizar_nome(texto: str) -> str:
    """Remove caracteres inválidos para nome de arquivo."""
    if not texto or not str(texto).strip():
        return "arquivo"
    texto = re.sub(r"[^\w\s\-áéíóúàèìòùãõâêîôûç]", "", str(texto).strip(), flags=re.IGNORECASE)
    texto = re.sub(r"[\s]+", "_", texto)
    return texto or "arquivo"


def converter_mp4_para_mp3(arquivo_mp4: str, arquivo_mp3: str) -> bool:
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
        subprocess.run(comando, check=True)
        return True
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        return None  # FFmpeg não encontrado


def _duracao_audio_segundos(caminho: str):
    """Retorna duração em segundos via ffprobe, ou None se falhar."""
    log = _log_compressao()
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        caminho,
    ]
    log.debug("ffprobe: %s", " ".join(cmd))
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except FileNotFoundError:
        log.error("ffprobe não encontrado no PATH")
        return None
    except subprocess.CalledProcessError as e:
        log.error("ffprobe falhou (código %s)", e.returncode)
        if e.stderr:
            log.error("ffprobe stderr: %s", e.stderr.strip()[:4000])
        return None
    try:
        dur = float(out.stdout.strip())
    except ValueError:
        log.error("ffprobe stdout inválido para duração: %r", (out.stdout or "")[:500])
        return None
    log.info("Duração detectada: %.2f s (%.1f min)", dur, dur / 60.0)
    return dur


def _caminho_mp3_comprimido(caminho_mp3: str) -> str:
    """Mesma pasta do original, sufixo _comprimido antes da extensão."""
    pasta, nome = os.path.split(caminho_mp3)
    base, ext = os.path.splitext(nome)
    return os.path.join(pasta, base + "_comprimido" + ext)


def comprimir_mp3_para_tamanho_max(arquivo_entrada: str, arquivo_saida: str, max_bytes: int = MAX_MP3_OUTPUT_BYTES):
    """
    Comprime MP3 com FFmpeg (libmp3lame) para ficar até max_bytes.
    Calcula bitrate a partir da duração; re-tenta com bitrate menor se necessário.
    Se o arquivo já for menor que max_bytes, copia para a saída sem re-encodar.
    Retorna True, False ou None (ffmpeg/ffprobe ausente).
    """
    log = _log_compressao()
    log.info("--- Início compressão ---")
    log.info("Entrada: %s", arquivo_entrada)
    log.info("Saída: %s", arquivo_saida)
    log.info("Limite alvo: %s (%.2f MB)", max_bytes, max_bytes / (1024.0 * 1024.0))

    if not os.path.isfile(arquivo_entrada):
        log.warning("Arquivo de entrada não existe")
        return False

    try:
        tamanho = os.path.getsize(arquivo_entrada)
    except OSError as e:
        log.error("Não foi possível obter tamanho da entrada: %s", e)
        return False

    log.info("Tamanho entrada: %s bytes (%.2f MB)", tamanho, tamanho / (1024.0 * 1024.0))

    if tamanho <= max_bytes:
        log.info("Arquivo já ≤ limite — copiando sem re-encodar (shutil.copy2)")
        try:
            shutil.copy2(arquivo_entrada, arquivo_saida)
            log.info("Cópia concluída: %s", arquivo_saida)
            return True
        except OSError as e:
            log.error("Falha ao copiar: %s", e)
            return False

    duracao = _duracao_audio_segundos(arquivo_entrada)
    if duracao is None or duracao <= 0:
        log.error("Duração inválida ou ffprobe indisponível — abortando compressão")
        return False

    # Margem para cabeçalhos e variação do encoder (~8%)
    alvo_bits = int(max_bytes * 8 * 0.92)
    kbps = int(alvo_bits / (duracao * 1000))
    kbps = max(MP3_BITRATE_MIN_KBPS, min(kbps, MP3_BITRATE_MAX_KBPS))
    log.info(
        "Bitrate inicial estimado: %d kbps (alvo_bits=%d, duração=%.2f s)",
        kbps, alvo_bits, duracao,
    )

    def rodar_ffmpeg(bitrate: int, tentativa: int):
        cmd = [
            "ffmpeg", "-y", "-i", arquivo_entrada,
            "-vn", "-acodec", "libmp3lame",
            "-b:a", "%dk" % bitrate,
            "-ar", "44100",
            arquivo_saida,
        ]
        log.debug("Tentativa %d — comando: %s", tentativa, " ".join(cmd))
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True)
        except FileNotFoundError:
            log.error("ffmpeg não encontrado no PATH")
            return None
        if proc.returncode != 0:
            log.error("ffmpeg falhou (código %s), bitrate=%d kbps", proc.returncode, bitrate)
            if proc.stderr:
                log.error("ffmpeg stderr:\n%s", proc.stderr.strip()[-6000:])
            if proc.stdout:
                log.debug("ffmpeg stdout:\n%s", proc.stdout.strip()[-2000:])
            return False
        if not os.path.isfile(arquivo_saida):
            log.error("ffmpeg não gerou o arquivo de saída: %s", arquivo_saida)
            return False
        sz = os.path.getsize(arquivo_saida)
        log.info(
            "Tentativa %d OK — bitrate %d kbps — tamanho saída: %s bytes (%.2f MB)",
            tentativa, bitrate, sz, sz / (1024.0 * 1024.0),
        )
        return True

    for tentativa in range(1, 7):
        r = rodar_ffmpeg(kbps, tentativa)
        if r is None:
            log.error("--- Fim compressão (ffmpeg ausente) ---")
            return None
        if not r:
            log.error("--- Fim compressão (erro ffmpeg) ---")
            return False
        if not os.path.isfile(arquivo_saida):
            return False
        sz_out = os.path.getsize(arquivo_saida)
        if sz_out <= max_bytes:
            log.info("Objetivo atingido: saída ≤ %.2f MB", max_bytes / (1024.0 * 1024.0))
            log.info("--- Fim compressão (sucesso) ---")
            return True
        kbps_novo = max(MP3_BITRATE_MIN_KBPS, int(kbps * 0.82))
        if kbps_novo >= kbps:
            log.error(
                "Bitrate já no mínimo (%d kbps); não dá para reduzir mais — saída %.2f MB",
                kbps,
                sz_out / (1024.0 * 1024.0),
            )
            break
        log.warning(
            "Saída ainda grande (%.2f MB > %.2f MB) — reduzindo bitrate %d → %d kbps",
            sz_out / (1024.0 * 1024.0),
            max_bytes / (1024.0 * 1024.0),
            kbps,
            kbps_novo,
        )
        kbps = kbps_novo

    ok = os.path.isfile(arquivo_saida) and os.path.getsize(arquivo_saida) <= max_bytes
    if ok:
        log.info("--- Fim compressão (sucesso após última tentativa) ---")
    else:
        log.warning(
            "--- Fim compressão — limite de 45 MB não atingido (tamanho final %.2f MB) ---",
            os.path.getsize(arquivo_saida) / (1024.0 * 1024.0) if os.path.isfile(arquivo_saida) else 0,
        )
    return ok


class ConverterApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Conversor MP4 → MP3 / Compressão de áudio")
        self.root.geometry("540x460")
        self.root.resizable(False, False)

        # Aba Conversão
        self.arquivo_mp4 = tk.StringVar()
        self.arquivo_mp3 = tk.StringVar()
        self.materia = tk.StringVar(value=MATERIAS[0] if MATERIAS else "")
        self.aula = tk.StringVar(value=AULAS[0] if AULAS else "")
        self.parte = tk.StringVar(value=PARTES[0] if PARTES else "")
        self.opcao = tk.StringVar(value="1")

        # Aba Compressão
        self.arquivo_mp3_compress = tk.StringVar()
        self.caminho_saida_comprimido = tk.StringVar()

        self._criar_interface()

    def _criar_interface(self):
        main_frame = ttk.Frame(self.root, padding=16)
        main_frame.pack(fill=tk.BOTH, expand=True)

        titulo = ttk.Label(
            main_frame,
            text="Conversor de Vídeo e Compressão de Áudio",
            font=("Segoe UI", 14, "bold"),
        )
        titulo.pack(pady=(0, 8))

        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        tab_conv = ttk.Frame(notebook, padding=12)
        tab_comp = ttk.Frame(notebook, padding=12)
        notebook.add(tab_conv, text="Conversão")
        notebook.add(tab_comp, text="Compressão")

        self._criar_aba_conversao(tab_conv)
        self._criar_aba_compressao(tab_comp)

    def _criar_aba_conversao(self, parent):
        # Seleção do arquivo MP4
        frame_mp4 = ttk.Frame(parent)
        frame_mp4.pack(fill=tk.X, pady=5)

        ttk.Label(frame_mp4, text="Arquivo MP4:", width=12).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(frame_mp4, textvariable=self.arquivo_mp4, width=40).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5)
        )
        ttk.Button(frame_mp4, text="Procurar...", command=self._selecionar_mp4).pack(side=tk.LEFT)

        frame_mp3 = ttk.Frame(parent)
        frame_mp3.pack(fill=tk.X, pady=5)

        ttk.Label(frame_mp3, text="Salvar como:", width=12).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(frame_mp3, textvariable=self.arquivo_mp3, width=40).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5)
        )
        ttk.Button(frame_mp3, text="Procurar...", command=self._selecionar_mp3).pack(side=tk.LEFT)

        frame_opcoes = ttk.Frame(parent)
        frame_opcoes.pack(fill=tk.X, pady=10)
        ttk.Label(frame_opcoes, text="Modo:", width=12).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Radiobutton(
            frame_opcoes, text="Com Matéria/Aula/Parte", value="1",
            variable=self.opcao, command=self._atualizar_interface,
        ).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(
            frame_opcoes, text="Nome Livre", value="2",
            variable=self.opcao, command=self._atualizar_interface,
        ).pack(side=tk.LEFT, padx=5)

        self.frame_materia = ttk.Frame(parent)
        ttk.Label(self.frame_materia, text="Matéria:", width=12).pack(side=tk.LEFT, padx=(0, 5))
        self.combo_materia = ttk.Combobox(
            self.frame_materia, textvariable=self.materia, values=MATERIAS,
            width=38, state="readonly",
        )
        self.combo_materia.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self.frame_aula = ttk.Frame(parent)
        ttk.Label(self.frame_aula, text="Aula:", width=12).pack(side=tk.LEFT, padx=(0, 5))
        self.combo_aula = ttk.Combobox(
            self.frame_aula, textvariable=self.aula, values=AULAS,
            width=38, state="readonly",
        )
        self.combo_aula.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self.frame_parte = ttk.Frame(parent)
        ttk.Label(self.frame_parte, text="Parte:", width=12).pack(side=tk.LEFT, padx=(0, 5))
        self.combo_parte = ttk.Combobox(
            self.frame_parte, textvariable=self.parte, values=PARTES,
            width=38, state="readonly",
        )
        self.combo_parte.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self._atualizar_interface()

        _trace_write(self.materia, self._atualizar_preview_mp3)
        _trace_write(self.aula, self._atualizar_preview_mp3)
        _trace_write(self.parte, self._atualizar_preview_mp3)
        _trace_write(self.arquivo_mp4, self._atualizar_preview_mp3)

        self.btn_converter = ttk.Button(parent, text="Converter para MP3", command=self._converter)
        self.btn_converter.pack(pady=16)

        self.progress = ttk.Progressbar(parent, mode="indeterminate")
        self.progress.pack(fill=tk.X, pady=5)

        self.status = ttk.Label(parent, text="Selecione um arquivo MP4 para converter.", foreground="gray")
        self.status.pack(pady=5)

    def _criar_aba_compressao(self, parent):
        info = ttk.Label(
            parent,
            text=(
                "Selecione um MP3 de até ~95 MB. O resultado terá no máximo 45 MB "
                "e será salvo na mesma pasta, com o sufixo _comprimido no nome."
            ),
            wraplength=480,
            justify=tk.LEFT,
        )
        info.pack(anchor=tk.W, pady=(0, 12))

        frame_in = ttk.Frame(parent)
        frame_in.pack(fill=tk.X, pady=5)
        ttk.Label(frame_in, text="Arquivo MP3:", width=12).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(frame_in, textvariable=self.arquivo_mp3_compress, width=40).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5)
        )
        ttk.Button(frame_in, text="Procurar...", command=self._selecionar_mp3_compress).pack(side=tk.LEFT)

        frame_out = ttk.Frame(parent)
        frame_out.pack(fill=tk.X, pady=5)
        ttk.Label(frame_out, text="Será salvo:", width=12).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(frame_out, textvariable=self.caminho_saida_comprimido, width=40, state="readonly").pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5)
        )

        self.lbl_tamanho_mp3 = ttk.Label(parent, text="", foreground="gray")
        self.lbl_tamanho_mp3.pack(anchor=tk.W, pady=4)

        self.btn_comprimir = ttk.Button(parent, text="Comprimir MP3", command=self._comprimir_mp3)
        self.btn_comprimir.pack(pady=16)

        self.progress_comp = ttk.Progressbar(parent, mode="indeterminate")
        self.progress_comp.pack(fill=tk.X, pady=5)

        self.status_comp = ttk.Label(parent, text="Selecione um arquivo MP3.", foreground="gray")
        self.status_comp.pack(pady=5)

    def _formatar_tamanho_mb(self, num_bytes: int) -> str:
        mb = num_bytes / (1024.0 * 1024.0)
        return "%.2f MB" % mb

    def _atualizar_info_compressao(self):
        caminho = self.arquivo_mp3_compress.get().strip()
        if caminho and os.path.isfile(caminho):
            try:
                sz = os.path.getsize(caminho)
                self.lbl_tamanho_mp3.config(
                    text="Tamanho: %s (máx. entrada ~95 MB)" % self._formatar_tamanho_mb(sz)
                )
            except OSError:
                self.lbl_tamanho_mp3.config(text="")
        else:
            self.lbl_tamanho_mp3.config(text="")

    def _selecionar_mp3_compress(self):
        arquivo = filedialog.askopenfilename(
            title="Selecionar MP3 para comprimir",
            filetypes=[("Áudio MP3", "*.mp3"), ("Todos os arquivos", "*.*")],
        )
        if arquivo:
            self.arquivo_mp3_compress.set(arquivo)
            saida = _caminho_mp3_comprimido(arquivo)
            self.caminho_saida_comprimido.set(saida)
            self._atualizar_info_compressao()
            self.status_comp.config(text="Arquivo selecionado.", foreground="gray")

    def _comprimir_mp3(self):
        log = _log_compressao()
        log.info("=== Clique em Comprimir MP3 (interface) ===")

        entrada = self.arquivo_mp3_compress.get().strip()
        if not entrada:
            log.warning("Validação: nenhum arquivo selecionado")
            messagebox.showwarning("Atenção", "Selecione um arquivo MP3.")
            return
        if not os.path.isfile(entrada):
            log.warning("Validação: arquivo não encontrado: %s", entrada)
            messagebox.showwarning("Atenção", "Arquivo não encontrado.")
            return
        if not entrada.lower().endswith(".mp3"):
            log.warning("Validação: extensão não é .mp3: %s", entrada)
            messagebox.showwarning("Atenção", "Use apenas arquivos .mp3 nesta aba.")
            return

        try:
            tamanho = os.path.getsize(entrada)
        except OSError as e:
            log.error("Validação: erro ao ler tamanho: %s", e)
            messagebox.showerror("Erro", "Não foi possível ler o arquivo.")
            return

        if tamanho > MAX_MP3_INPUT_BYTES:
            log.warning(
                "Validação: arquivo %.2f MB excede limite de entrada ~95 MB",
                tamanho / (1024.0 * 1024.0),
            )
            messagebox.showwarning(
                "Arquivo grande demais",
                "O arquivo ultrapassa ~95 MB.\n"
                "Reduza o tamanho ou use outro arquivo.",
            )
            return

        saida = _caminho_mp3_comprimido(entrada)
        self.caminho_saida_comprimido.set(saida)
        log.info("Caminho de saída definido: %s", saida)

        self.btn_comprimir.config(state=tk.DISABLED)
        self.progress_comp.start(10)
        self.status_comp.config(text="Comprimindo...", foreground="blue")
        self.root.update()

        resultado = comprimir_mp3_para_tamanho_max(entrada, saida)

        self.progress_comp.stop()
        self.btn_comprimir.config(state=tk.NORMAL)

        log.info("Resultado da compressão (retorno função): %r", resultado)

        if resultado is True:
            try:
                sz_out = os.path.getsize(saida)
            except OSError:
                sz_out = 0
            if tamanho <= MAX_MP3_OUTPUT_BYTES:
                log.info("UI: concluído — cópia sem re-encode (entrada já ≤ 45 MB), saída %s", self._formatar_tamanho_mb(sz_out))
                self.status_comp.config(
                    text="Arquivo já estava abaixo de 45 MB — cópia salva com sufixo _comprimido.",
                    foreground="green",
                )
                messagebox.showinfo(
                    "Concluído",
                    "O arquivo já tinha menos de 45 MB.\n"
                    "Foi criada uma cópia em:\n%s" % saida,
                )
            elif sz_out <= MAX_MP3_OUTPUT_BYTES:
                log.info("UI: compressão OK — saída %s (≤ 45 MB)", self._formatar_tamanho_mb(sz_out))
                self.status_comp.config(text="Compressão concluída (≤ 45 MB).", foreground="green")
                messagebox.showinfo("Sucesso", "Arquivo salvo em:\n%s\n\nTamanho: %s" % (saida, self._formatar_tamanho_mb(sz_out)))
            else:
                log.warning("UI: compressão terminou mas saída ainda > 45 MB: %s", self._formatar_tamanho_mb(sz_out))
                self.status_comp.config(
                    text="Aviso: saída ainda acima de 45 MB (áudio muito longo).",
                    foreground="orange",
                )
                messagebox.showwarning(
                    "Atenção",
                    "Mesmo no bitrate mínimo, o arquivo pode exceder 45 MB por ser muito longo.\n"
                    "Arquivo gerado:\n%s\nTamanho: %s" % (saida, self._formatar_tamanho_mb(sz_out)),
                )
        elif resultado is False:
            log.error("UI: compressão retornou False (erro de processamento)")
            self.status_comp.config(text="Erro na compressão.", foreground="red")
            messagebox.showerror(
                "Erro",
                "Não foi possível comprimir.\nVerifique se o arquivo é um MP3 válido.",
            )
        else:
            log.error("UI: compressão retornou None (ffmpeg/ffprobe ausente)")
            self.status_comp.config(text="FFmpeg/ffprobe não encontrado.", foreground="red")
            messagebox.showerror(
                "Erro",
                "FFmpeg e ffprobe precisam estar instalados e no PATH.",
            )

    def _atualizar_interface(self):
        """Mostra ou oculta campos baseado na opção selecionada."""
        if self.opcao.get() == "1":
            self.frame_materia.pack(fill=tk.X, pady=5)
            self.frame_aula.pack(fill=tk.X, pady=5)
            self.frame_parte.pack(fill=tk.X, pady=5)
        else:
            self.frame_materia.pack_forget()
            self.frame_aula.pack_forget()
            self.frame_parte.pack_forget()
        self._atualizar_preview_mp3()

    def _atualizar_preview_mp3(self, *_):
        """Atualiza o campo 'Salvar como' com o nome gerado automaticamente."""
        mp4 = self.arquivo_mp4.get().strip()
        if mp4 and os.path.isfile(mp4):
            pasta = os.path.dirname(mp4)
            nome_mp3 = self._nome_mp3_automatico()
            self.arquivo_mp3.set(os.path.join(pasta, nome_mp3))

    def _nome_mp3_automatico(self) -> str:
        """Gera o nome do MP3 baseado na opção selecionada."""
        data_atual = datetime.now().strftime("%Y-%m-%d")

        if self.opcao.get() == "1":
            parte_materia = _sanitizar_nome(self.materia.get())
            parte_aula = _sanitizar_nome(self.aula.get())
            parte_parte = _sanitizar_nome(self.parte.get())
            return "%s_%s_%s_%s.mp3" % (parte_materia, parte_aula, parte_parte, data_atual)
        else:
            mp4 = self.arquivo_mp4.get().strip()
            if mp4 and os.path.isfile(mp4):
                nome_base = os.path.splitext(os.path.basename(mp4))[0]
                nome_sanitizado = _sanitizar_nome(nome_base)
                return "%s_%s.mp3" % (nome_sanitizado, data_atual)
            return "audio_%s.mp3" % data_atual

    def _selecionar_mp4(self):
        arquivo = filedialog.askopenfilename(
            title="Selecionar arquivo MP4",
            filetypes=[("Vídeos MP4", "*.mp4"), ("Todos os arquivos", "*.*")],
        )
        if arquivo:
            self.arquivo_mp4.set(arquivo)
            pasta = os.path.dirname(arquivo)
            nome_mp3 = self._nome_mp3_automatico()
            self.arquivo_mp3.set(os.path.join(pasta, nome_mp3))
            self.status.config(text="Arquivo selecionado.", foreground="gray")

    def _selecionar_mp3(self):
        arquivo = filedialog.asksaveasfilename(
            title="Salvar MP3 como",
            defaultextension=".mp3",
            filetypes=[("Áudio MP3", "*.mp3"), ("Todos os arquivos", "*.*")],
        )
        if arquivo:
            self.arquivo_mp3.set(arquivo)
            self.status.config(text="Destino definido.", foreground="gray")

    def _converter(self):
        mp4 = self.arquivo_mp4.get().strip()
        mp3 = self.arquivo_mp3.get().strip()

        if not mp4:
            messagebox.showwarning("Atenção", "Selecione um arquivo MP4.")
            return

        if not mp3:
            pasta = os.path.dirname(mp4)
            nome_mp3 = self._nome_mp3_automatico()
            mp3 = os.path.join(pasta, nome_mp3)
            self.arquivo_mp3.set(mp3)

        self.btn_converter.config(state=tk.DISABLED)
        self.progress.start(10)
        self.status.config(text="Convertendo...", foreground="blue")

        self.root.update()

        resultado = converter_mp4_para_mp3(mp4, mp3)

        self.progress.stop()
        self.btn_converter.config(state=tk.NORMAL)

        if resultado is True:
            self.status.config(text="Conversão concluída com sucesso!", foreground="green")
            messagebox.showinfo("Sucesso", "Arquivo salvo em:\n%s" % mp3)
        elif resultado is False:
            self.status.config(text="Erro na conversão.", foreground="red")
            messagebox.showerror(
                "Erro",
                "Ocorreu um erro durante a conversão.\nVerifique se o FFmpeg está instalado e se o arquivo é válido.",
            )
        else:
            self.status.config(text="FFmpeg não encontrado.", foreground="red")
            messagebox.showerror(
                "Erro",
                "FFmpeg não foi encontrado.\nInstale o FFmpeg e adicione-o ao PATH do sistema.",
            )

    def executar(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = ConverterApp()
    app.executar()
