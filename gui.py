"""
Interface visual para conversão de MP4 para MP3
"""
import os
import re
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

AULAS = ["Aula 1", "Aula 2"]


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


class ConverterApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Conversor MP4 → MP3")
        self.root.geometry("520x340")
        self.root.resizable(False, False)

        # Variáveis
        self.arquivo_mp4 = tk.StringVar()
        self.arquivo_mp3 = tk.StringVar()
        self.materia = tk.StringVar(value=MATERIAS[0] if MATERIAS else "")
        self.aula = tk.StringVar(value=AULAS[0] if AULAS else "")

        self._criar_interface()

    def _criar_interface(self):
        # Frame principal
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Título
        titulo = ttk.Label(main_frame, text="Conversor de Vídeo para Áudio", font=("Segoe UI", 14, "bold"))
        titulo.pack(pady=(0, 15))

        # Seleção do arquivo MP4
        frame_mp4 = ttk.Frame(main_frame)
        frame_mp4.pack(fill=tk.X, pady=5)

        ttk.Label(frame_mp4, text="Arquivo MP4:", width=12).pack(side=tk.LEFT, padx=(0, 5))
        entry_mp4 = ttk.Entry(frame_mp4, textvariable=self.arquivo_mp4, width=45)
        entry_mp4.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(frame_mp4, text="Procurar...", command=self._selecionar_mp4).pack(side=tk.LEFT)

        # Seleção do arquivo de saída MP3
        frame_mp3 = ttk.Frame(main_frame)
        frame_mp3.pack(fill=tk.X, pady=5)

        ttk.Label(frame_mp3, text="Salvar como:", width=12).pack(side=tk.LEFT, padx=(0, 5))
        entry_mp3 = ttk.Entry(frame_mp3, textvariable=self.arquivo_mp3, width=45)
        entry_mp3.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(frame_mp3, text="Procurar...", command=self._selecionar_mp3).pack(side=tk.LEFT)

        # Matéria
        frame_materia = ttk.Frame(main_frame)
        frame_materia.pack(fill=tk.X, pady=5)
        ttk.Label(frame_materia, text="Matéria:", width=12).pack(side=tk.LEFT, padx=(0, 5))
        combo_materia = ttk.Combobox(
            frame_materia, textvariable=self.materia, values=MATERIAS,
            width=42, state="readonly"
        )
        combo_materia.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        # Aula
        frame_aula = ttk.Frame(main_frame)
        frame_aula.pack(fill=tk.X, pady=5)
        ttk.Label(frame_aula, text="Aula:", width=12).pack(side=tk.LEFT, padx=(0, 5))
        combo_aula = ttk.Combobox(
            frame_aula, textvariable=self.aula, values=AULAS,
            width=42, state="readonly"
        )
        combo_aula.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        # Atualizar preview do nome MP3 quando mudar matéria ou aula
        self.materia.trace_add("write", self._atualizar_preview_mp3)
        self.aula.trace_add("write", self._atualizar_preview_mp3)

        # Botão converter
        self.btn_converter = ttk.Button(main_frame, text="Converter para MP3", command=self._converter)
        self.btn_converter.pack(pady=20)

        # Barra de progresso (indeterminada durante conversão)
        self.progress = ttk.Progressbar(main_frame, mode="indeterminate")
        self.progress.pack(fill=tk.X, pady=5)

        # Status
        self.status = ttk.Label(main_frame, text="Selecione um arquivo MP4 para converter.", foreground="gray")
        self.status.pack(pady=5)

    def _atualizar_preview_mp3(self, *_):
        """Atualiza o campo 'Salvar como' com o nome materia_aula_data."""
        mp4 = self.arquivo_mp4.get().strip()
        if mp4 and os.path.isfile(mp4):
            pasta = os.path.dirname(mp4)
            self.arquivo_mp3.set(os.path.join(pasta, self._nome_mp3_automatico()))

    def _nome_mp3_automatico(self) -> str:
        """Gera o nome do MP3: materia_aula_dataAtual.mp3"""
        data_atual = datetime.now().strftime("%Y-%m-%d")
        parte_materia = _sanitizar_nome(self.materia.get())
        parte_aula = _sanitizar_nome(self.aula.get())
        return f"{parte_materia}_{parte_aula}_{data_atual}.mp3"

    def _selecionar_mp4(self):
        arquivo = filedialog.askopenfilename(
            title="Selecionar arquivo MP4",
            filetypes=[("Vídeos MP4", "*.mp4"), ("Todos os arquivos", "*.*")]
        )
        if arquivo:
            self.arquivo_mp4.set(arquivo)
            # Sugerir nome do MP3 (materia_aula_data) na mesma pasta do MP4
            if not self.arquivo_mp3.get():
                pasta = os.path.dirname(arquivo)
                nome_mp3 = self._nome_mp3_automatico()
                self.arquivo_mp3.set(os.path.join(pasta, nome_mp3))
            self.status.config(text="Arquivo selecionado.", foreground="gray")

    def _selecionar_mp3(self):
        arquivo = filedialog.asksaveasfilename(
            title="Salvar MP3 como",
            defaultextension=".mp3",
            filetypes=[("Áudio MP3", "*.mp3"), ("Todos os arquivos", "*.*")]
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

        # Nome final sempre: materia_aula_dataAtual.mp3 (na mesma pasta do MP4)
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
            messagebox.showinfo("Sucesso", f"Arquivo salvo em:\n{mp3}")
        elif resultado is False:
            self.status.config(text="Erro na conversão.", foreground="red")
            messagebox.showerror("Erro", "Ocorreu um erro durante a conversão.\nVerifique se o FFmpeg está instalado e se o arquivo é válido.")
        else:
            self.status.config(text="FFmpeg não encontrado.", foreground="red")
            messagebox.showerror("Erro", "FFmpeg não foi encontrado.\nInstale o FFmpeg e adicione-o ao PATH do sistema.")

    def executar(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = ConverterApp()
    app.executar()
