#!/usr/bin/env python3
"""
Descargador de audio y video de YouTube (estilo aTubeCatcher).

Usa yt-dlp para descargar y ffmpeg para unir video+audio y convertir a MP3.

Modo gráfico (sin argumentos):
    python descargador.py

Modo consola:
    python descargador.py URL [URL ...] [--audio] [--calidad 720] [--formato mp3] [--carpeta DIR]
"""

import argparse
import os
import queue
import shutil
import sys
import threading

try:
    import yt_dlp
except ImportError:
    print("Falta yt-dlp. Instalalo con:  pip install -U yt-dlp")
    sys.exit(1)


CARPETA_POR_DEFECTO = os.path.join(os.path.expanduser("~"), "Descargas", "YouTube")

CALIDADES_VIDEO = ["Mejor", "2160", "1440", "1080", "720", "480", "360", "240"]
FORMATOS_VIDEO = ["mp4", "mkv", "webm"]
CALIDADES_AUDIO = ["320", "256", "192", "128", "96"]
FORMATOS_AUDIO = ["mp3", "m4a", "opus", "wav", "flac"]


def hay_ffmpeg():
    return shutil.which("ffmpeg") is not None


def construir_opciones(carpeta, solo_audio, calidad, formato, playlist,
                       hook_progreso=None, logger=None):
    """Arma el diccionario de opciones de yt-dlp según lo elegido."""
    opciones = {
        "outtmpl": os.path.join(carpeta, "%(title)s.%(ext)s"),
        "noplaylist": not playlist,
        "ignoreerrors": True,
        "restrictfilenames": False,
        "windowsfilenames": True,
        "quiet": True,
        "no_warnings": True,
    }
    if playlist:
        opciones["outtmpl"] = os.path.join(
            carpeta, "%(playlist_title|)s", "%(playlist_index|)s%(playlist_index& - |)s%(title)s.%(ext)s"
        )
    if hook_progreso:
        opciones["progress_hooks"] = [hook_progreso]
    if logger:
        opciones["logger"] = logger

    if solo_audio:
        opciones["format"] = "bestaudio/best"
        if hay_ffmpeg():
            opciones["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": formato,
                    "preferredquality": str(calidad),
                },
                {"key": "FFmpegMetadata"},
            ]
    else:
        filtro = "" if calidad in ("Mejor", None) else f"[height<={calidad}]"
        if hay_ffmpeg():
            if formato == "mp4":
                # Preferir códecs compatibles con MP4 (h264/aac) y si no, lo mejor disponible.
                opciones["format"] = (
                    f"bestvideo{filtro}[ext=mp4]+bestaudio[ext=m4a]/"
                    f"bestvideo{filtro}+bestaudio/best{filtro}/best"
                )
            else:
                opciones["format"] = f"bestvideo{filtro}+bestaudio/best{filtro}/best"
            opciones["merge_output_format"] = formato
            opciones["postprocessors"] = [{"key": "FFmpegMetadata"}]
        else:
            # Sin ffmpeg no se pueden unir pistas: bajar un archivo que ya traiga ambas.
            opciones["format"] = f"best{filtro}[acodec!=none][vcodec!=none]/best"

    return opciones


def descargar(urls, carpeta, solo_audio, calidad, formato, playlist,
              hook_progreso=None, logger=None):
    os.makedirs(carpeta, exist_ok=True)
    opciones = construir_opciones(carpeta, solo_audio, calidad, formato,
                                  playlist, hook_progreso, logger)
    with yt_dlp.YoutubeDL(opciones) as ydl:
        return ydl.download(urls)


# --------------------------------------------------------------------------- #
# Modo consola
# --------------------------------------------------------------------------- #

def main_consola(argv):
    parser = argparse.ArgumentParser(description="Descargar audio y video de YouTube.")
    parser.add_argument("urls", nargs="+", help="Enlaces de YouTube")
    parser.add_argument("-a", "--audio", action="store_true", help="Descargar solo el audio")
    parser.add_argument("-c", "--calidad", default=None,
                        help="Video: altura máx. (1080, 720...). Audio: kbps (320, 192...)")
    parser.add_argument("-f", "--formato", default=None,
                        help="Video: mp4/mkv/webm. Audio: mp3/m4a/opus/wav/flac")
    parser.add_argument("-d", "--carpeta", default=CARPETA_POR_DEFECTO, help="Carpeta de destino")
    parser.add_argument("-p", "--playlist", action="store_true", help="Descargar la lista completa")
    args = parser.parse_args(argv)

    if args.audio:
        calidad = args.calidad or "192"
        formato = args.formato or "mp3"
    else:
        calidad = args.calidad or "Mejor"
        formato = args.formato or "mp4"

    if not hay_ffmpeg():
        print("Aviso: no se encontró ffmpeg. Sin él no se puede convertir a MP3 "
              "ni unir video+audio en alta calidad.")

    def hook(d):
        if d["status"] == "downloading":
            print(f"\r  {d.get('_percent_str', '').strip():>7}  "
                  f"{d.get('_speed_str', '').strip():>12}  "
                  f"ETA {d.get('_eta_str', '').strip()}", end="", flush=True)
        elif d["status"] == "finished":
            print(f"\r  Descargado: {os.path.basename(d['filename'])}")

    codigo = descargar(args.urls, args.carpeta, args.audio, calidad, formato,
                       args.playlist, hook)
    print("Listo." if codigo == 0 else "Terminó con errores.")
    print(f"Archivos en: {args.carpeta}")
    return codigo


# --------------------------------------------------------------------------- #
# Modo gráfico
# --------------------------------------------------------------------------- #

def main_gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    eventos = queue.Queue()

    class LoggerCola:
        def debug(self, msg):
            if not msg.startswith("[debug]"):
                self.info(msg)

        def info(self, msg):
            eventos.put(("log", msg))

        def warning(self, msg):
            eventos.put(("log", f"Aviso: {msg}"))

        def error(self, msg):
            eventos.put(("log", msg))

    ventana = tk.Tk()
    ventana.title("Descargador de YouTube")
    ventana.geometry("720x560")
    ventana.minsize(600, 480)

    marco = ttk.Frame(ventana, padding=12)
    marco.pack(fill="both", expand=True)

    # Enlaces
    ttk.Label(marco, text="Enlaces de YouTube (uno por línea):").pack(anchor="w")
    caja_urls = tk.Text(marco, height=5, wrap="none")
    caja_urls.pack(fill="x", pady=(2, 4))

    fila_pegar = ttk.Frame(marco)
    fila_pegar.pack(fill="x")

    def pegar():
        try:
            texto = ventana.clipboard_get().strip()
        except tk.TclError:
            return
        if texto:
            actual = caja_urls.get("1.0", "end").strip()
            caja_urls.insert("end", ("\n" if actual else "") + texto)

    ttk.Button(fila_pegar, text="Pegar", command=pegar).pack(side="left")
    ttk.Button(fila_pegar, text="Limpiar",
               command=lambda: caja_urls.delete("1.0", "end")).pack(side="left", padx=6)
    var_playlist = tk.BooleanVar(value=False)
    ttk.Checkbutton(fila_pegar, text="Descargar lista de reproducción completa",
                    variable=var_playlist).pack(side="left", padx=12)

    # Opciones
    opciones = ttk.LabelFrame(marco, text="Opciones", padding=8)
    opciones.pack(fill="x", pady=10)

    var_tipo = tk.StringVar(value="video")
    var_calidad = tk.StringVar()
    var_formato = tk.StringVar()

    ttk.Label(opciones, text="Tipo:").grid(row=0, column=0, sticky="w")
    ttk.Radiobutton(opciones, text="Video", value="video", variable=var_tipo,
                    command=lambda: actualizar_opciones()).grid(row=0, column=1, sticky="w")
    ttk.Radiobutton(opciones, text="Solo audio", value="audio", variable=var_tipo,
                    command=lambda: actualizar_opciones()).grid(row=0, column=2, sticky="w")

    ttk.Label(opciones, text="Formato:").grid(row=1, column=0, sticky="w", pady=4)
    combo_formato = ttk.Combobox(opciones, textvariable=var_formato, state="readonly", width=10)
    combo_formato.grid(row=1, column=1, sticky="w")

    etiqueta_calidad = ttk.Label(opciones, text="Calidad:")
    etiqueta_calidad.grid(row=1, column=2, sticky="w", padx=(12, 0))
    combo_calidad = ttk.Combobox(opciones, textvariable=var_calidad, state="readonly", width=10)
    combo_calidad.grid(row=1, column=3, sticky="w")

    def actualizar_opciones():
        if var_tipo.get() == "audio":
            combo_formato["values"] = FORMATOS_AUDIO
            combo_calidad["values"] = CALIDADES_AUDIO
            var_formato.set("mp3")
            var_calidad.set("192")
            etiqueta_calidad.config(text="Calidad (kbps):")
        else:
            combo_formato["values"] = FORMATOS_VIDEO
            combo_calidad["values"] = CALIDADES_VIDEO
            var_formato.set("mp4")
            var_calidad.set("1080")
            etiqueta_calidad.config(text="Resolución (p):")

    actualizar_opciones()

    ttk.Label(opciones, text="Guardar en:").grid(row=2, column=0, sticky="w")
    var_carpeta = tk.StringVar(value=CARPETA_POR_DEFECTO)
    ttk.Entry(opciones, textvariable=var_carpeta).grid(row=2, column=1, columnspan=3, sticky="ew")

    def elegir_carpeta():
        carpeta = filedialog.askdirectory(initialdir=var_carpeta.get() or os.path.expanduser("~"))
        if carpeta:
            var_carpeta.set(carpeta)

    ttk.Button(opciones, text="Examinar...", command=elegir_carpeta).grid(row=2, column=4, padx=6)

    def abrir_carpeta():
        carpeta = var_carpeta.get()
        os.makedirs(carpeta, exist_ok=True)
        if sys.platform.startswith("win"):
            os.startfile(carpeta)
        elif sys.platform == "darwin":
            os.system(f'open "{carpeta}"')
        else:
            os.system(f'xdg-open "{carpeta}"')

    ttk.Button(opciones, text="Abrir", command=abrir_carpeta).grid(row=2, column=5)
    opciones.columnconfigure(3, weight=1)

    # Botón de descarga y progreso
    boton = ttk.Button(marco, text="Descargar")
    boton.pack(pady=(0, 8))

    barra = ttk.Progressbar(marco, mode="determinate", maximum=100)
    barra.pack(fill="x")
    var_estado = tk.StringVar(value="Listo.")
    ttk.Label(marco, textvariable=var_estado).pack(anchor="w", pady=(2, 6))

    # Registro
    registro = tk.Text(marco, height=10, state="disabled", wrap="word")
    registro.pack(fill="both", expand=True)

    def escribir_log(texto):
        registro.config(state="normal")
        registro.insert("end", texto + "\n")
        registro.see("end")
        registro.config(state="disabled")

    if not hay_ffmpeg():
        escribir_log("Aviso: no se encontró ffmpeg. Instalalo para convertir a MP3 "
                     "y bajar video en alta calidad (https://ffmpeg.org).")

    def hook(d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            porcentaje = d.get("downloaded_bytes", 0) * 100 / total if total else 0
            nombre = os.path.basename(d.get("filename", ""))
            eventos.put(("progreso", porcentaje,
                         f"{nombre}  {d.get('_speed_str', '').strip()}  "
                         f"ETA {d.get('_eta_str', '').strip()}"))
        elif d["status"] == "finished":
            eventos.put(("progreso", 100, "Procesando..."))

    def trabajo(urls, carpeta, solo_audio, calidad, formato, playlist):
        try:
            codigo = descargar(urls, carpeta, solo_audio, calidad, formato,
                               playlist, hook, LoggerCola())
            eventos.put(("fin", codigo == 0))
        except Exception as e:  # noqa: BLE001 - mostrar cualquier error al usuario
            eventos.put(("log", f"Error: {e}"))
            eventos.put(("fin", False))

    def iniciar():
        urls = [u.strip() for u in caja_urls.get("1.0", "end").splitlines() if u.strip()]
        if not urls:
            messagebox.showwarning("Faltan enlaces", "Pegá al menos un enlace de YouTube.")
            return
        boton.config(state="disabled")
        barra["value"] = 0
        var_estado.set("Iniciando...")
        escribir_log(f"--- Descargando {len(urls)} enlace(s) ---")
        threading.Thread(
            target=trabajo,
            args=(urls, var_carpeta.get(), var_tipo.get() == "audio",
                  var_calidad.get(), var_formato.get(), var_playlist.get()),
            daemon=True,
        ).start()

    boton.config(command=iniciar)

    def procesar_eventos():
        try:
            while True:
                evento = eventos.get_nowait()
                if evento[0] == "log":
                    escribir_log(evento[1])
                elif evento[0] == "progreso":
                    barra["value"] = evento[1]
                    var_estado.set(evento[2])
                elif evento[0] == "fin":
                    boton.config(state="normal")
                    if evento[1]:
                        var_estado.set("¡Descarga completa!")
                        escribir_log("Descarga completa.")
                    else:
                        var_estado.set("Terminó con errores (ver registro).")
        except queue.Empty:
            pass
        ventana.after(100, procesar_eventos)

    procesar_eventos()
    ventana.mainloop()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        sys.exit(main_consola(sys.argv[1:]))
    main_gui()
