"""Download separate 720p-or-lower video and audio streams without login."""
import sys
from pytubefix import YouTube

video = YouTube(sys.argv[1], client="WEB", use_oauth=False, allow_oauth_cache=False)
stream = (video.streams.filter(only_video=True)
          .filter(custom_filter_functions=[lambda s: int(s.resolution.rstrip('p')) <= 720])
          .order_by("resolution").desc().first())
if stream is None:
    raise RuntimeError("Nenhuma faixa de vídeo até 720p disponível")
stream.download(output_path=sys.argv[2], filename="video." + stream.subtype)
audio = video.streams.filter(only_audio=True).order_by("abr").desc().first()
audio.download(output_path=sys.argv[2], filename="audio." + audio.subtype)
