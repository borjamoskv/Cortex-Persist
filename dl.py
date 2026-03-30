import sys

import yt_dlp

url = "https://www.youtube.com/watch?v=8KTMElsvohE"
opts = {
    'format': 'bestaudio/best',
    'outtmpl': '/Users/borjafernandezangulo/30_CORTEX/shock_source.%(ext)s',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'wav',
    }],
}

try:
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
