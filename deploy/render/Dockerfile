FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*
# Deno provides a supported JS runtime independently of Debian's Node version.
COPY --from=denoland/deno:bin-2.5.6 /deno /usr/local/bin/deno
RUN pip install --no-cache-dir --pre 'yt-dlp[default]'
WORKDIR /app
COPY deploy/render/server.py /app/server.py
RUN useradd --create-home appuser
USER appuser
ENV PORT=10000
CMD ["python", "server.py"]
