"""
Interface visual para conversão de MP4 para MP3
"""
import os
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


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
        self.root.geometry("520x220")
        self.root.resizable(False, False)

        # Variáveis
        self.arquivo_mp4 = tk.StringVar()
        self.arquivo_mp3 = tk.StringVar()

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

        # Botão converter
        self.btn_converter = ttk.Button(main_frame, text="Converter para MP3", command=self._converter)
        self.btn_converter.pack(pady=20)

        # Barra de progresso (indeterminada durante conversão)
        self.progress = ttk.Progressbar(main_frame, mode="indeterminate")
        self.progress.pack(fill=tk.X, pady=5)

        # Status
        self.status = ttk.Label(main_frame, text="Selecione um arquivo MP4 para converter.", foreground="gray")
        self.status.pack(pady=5)

    def _selecionar_mp4(self):
        arquivo = filedialog.askopenfilename(
            title="Selecionar arquivo MP4",
            filetypes=[("Vídeos MP4", "*.mp4"), ("Todos os arquivos", "*.*")]
        )
        if arquivo:
            self.arquivo_mp4.set(arquivo)
            # Sugerir nome do MP3 na mesma pasta
            if not self.arquivo_mp3.get():
                base = os.path.splitext(arquivo)[0]
                self.arquivo_mp3.set(base + ".mp3")
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

        if not mp3:
            base = os.path.splitext(mp4)[0]
            mp3 = base + ".mp3"
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
