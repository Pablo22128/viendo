# Descargador de YouTube (estilo aTubeCatcher)

Programa en Python para descargar **video** (MP4/MKV/WEBM) o **solo audio** (MP3/M4A/OPUS/WAV/FLAC) de YouTube.
Tiene ventana gráfica y también se puede usar desde la consola. Usa [yt-dlp](https://github.com/yt-dlp/yt-dlp).

## Windows sin instalar nada

Usá `DescargadorYouTube.exe`: es un solo archivo que ya trae Python, yt-dlp, ffmpeg y deno.
Doble clic y listo. Si Windows muestra "Windows protegió su PC", tocá *Más información* →
*Ejecutar de todas formas* (pasa con cualquier programa sin firma digital).

Para generar el .exe en Windows con Python instalado:
```
pip install pyinstaller "yt-dlp[default]"
pyinstaller --onefile --windowed --name DescargadorYouTube --collect-all yt_dlp_ejs ^
  --add-binary "ffmpeg.exe;bin" --add-binary "deno.exe;bin" descargador.py
```
(con `ffmpeg.exe` y `deno.exe` en la misma carpeta que `descargador.py`).

## Instalación (para usar con Python)

1. Python 3.8 o superior (en Linux puede hacer falta `sudo apt install python3-tk` para la ventana).
2. Instalar yt-dlp:
   ```
   pip install -r requirements.txt
   ```
3. Instalar **ffmpeg** (necesario para convertir a MP3 y para video en 1080p o más):
   - Windows: `winget install ffmpeg`
   - Linux: `sudo apt install ffmpeg`
   - macOS: `brew install ffmpeg`

## Uso con ventana

```
python descargador.py
```

Pegá uno o varios enlaces (uno por línea), elegí *Video* o *Solo audio*, el formato, la calidad
y la carpeta, y apretá **Descargar**. Marcá "lista de reproducción completa" para bajar playlists enteras.

## Uso desde la consola

```
# Video en la mejor calidad (MP4)
python descargador.py "https://www.youtube.com/watch?v=XXXX"

# Video en 720p
python descargador.py "URL" --calidad 720

# Audio MP3 a 320 kbps
python descargador.py "URL" --audio --calidad 320

# Playlist completa en MP3 a una carpeta
python descargador.py "URL_DE_LA_LISTA" --audio --playlist --carpeta ./musica
```

Por defecto los archivos se guardan en la carpeta Descargas, dentro de `YouTube`.

Si YouTube cambia algo y deja de funcionar, actualizá yt-dlp: `pip install -U yt-dlp`.

> Descargá solo contenido que tengas derecho a descargar.
