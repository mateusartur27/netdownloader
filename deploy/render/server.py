"""Small authenticated cloud download probe; no persistent files or account cookies."""
import base64
import hmac
import json
import os
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

LOCK = threading.Lock()
PASSWORD = os.environ.get("APP_PASSWORD", "")


def allowed_url(url):
    try:
        parsed = urlsplit(url)
        return (parsed.scheme == "https" and parsed.hostname in
                {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}
                and parsed.port in (None, 443) and not parsed.username and not parsed.password)
    except (ValueError, TypeError):
        return False


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, data, content_type="application/json"):
        body = data.encode() if isinstance(data, str) else json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def authenticated(self):
        expected = "Basic " + base64.b64encode(f"admin:{PASSWORD}".encode()).decode()
        if PASSWORD and hmac.compare_digest(self.headers.get("Authorization", ""), expected):
            return True
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="NetDownloader"')
        self.send_header("Content-Length", "0")
        self.end_headers()
        return False

    def do_GET(self):
        if self.path == "/health":
            return self.reply(200, {"status": "ok"})
        if not self.authenticated():
            return
        self.reply(200, '''<!doctype html><html lang="pt-BR"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>NetDownloader — teste na nuvem</title>
<body style="font:18px system-ui;max-width:700px;margin:48px auto;padding:20px">
<h1>Teste de download na nuvem</h1><p>Cole uma URL pública do YouTube.</p>
<form><input id="url" type="url" required placeholder="https://www.youtube.com/watch?v=..."
style="width:95%;padding:12px"><button style="margin:16px 0;padding:12px">Testar download</button></form>
<pre id="result" style="white-space:pre-wrap"></pre>
<script>document.querySelector('form').onsubmit=async e=>{e.preventDefault();
const button=document.querySelector('button');button.disabled=true;
document.querySelector('#result').textContent='Baixando e validando. Aguarde...';
try{const response=await fetch('/probe',{method:'POST',headers:{'Content-Type':'application/json'},
body:JSON.stringify({url:document.querySelector('#url').value})});
document.querySelector('#result').textContent=JSON.stringify(await response.json(),null,2);
}catch(error){document.querySelector('#result').textContent='Falha de conexão. Tente novamente após o serviço iniciar.';}
finally{button.disabled=false;}};</script></body></html>''', "text/html; charset=utf-8")

    def do_POST(self):
        if not self.authenticated():
            return
        if self.path != "/probe":
            return self.reply(404, {"error": "Rota inexistente"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > 4096:
                raise ValueError()
            url = json.loads(self.rfile.read(length)).get("url")
            if not allowed_url(url):
                raise ValueError()
        except (ValueError, AttributeError, TypeError):
            return self.reply(400, {"error": "Informe uma URL HTTPS pública do YouTube"})
        if not LOCK.acquire(blocking=False):
            return self.reply(409, {"error": "Já existe um teste em andamento"})
        try:
            with tempfile.TemporaryDirectory() as directory:
                command = [sys.executable, "-m", "yt_dlp", "--ignore-config", "--no-playlist",
                           "--js-runtimes", "deno", "--max-filesize", "50M", "--socket-timeout", "20",
                           "--retries", "1", "--fragment-retries", "1", "--sleep-requests", "1",
                           "-f", "bv*[height<=480]+ba/b[height<=480]", "--merge-output-format", "mkv",
                           "-o", str(Path(directory) / "video.%(ext)s"), url]
                try:
                    result = subprocess.run(command, capture_output=True, text=True, timeout=180, check=False)
                except subprocess.TimeoutExpired:
                    return self.reply(504, {"ok": False, "error": "Tempo limite de 3 minutos"})
                files = [p for p in Path(directory).iterdir() if p.suffix in {".mp4", ".mkv", ".webm"}]
                if result.returncode or len(files) != 1:
                    message = result.stderr.lower()
                    reason = "YouTube exigiu confirmação de bot" if "bot" in message else "Download recusado ou indisponível"
                    return self.reply(422, {"ok": False, "error": reason})
                probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                        "format=duration:stream=codec_type", "-of", "json", str(files[0])],
                                       capture_output=True, text=True, timeout=20, check=False)
                details = json.loads(probe.stdout) if probe.returncode == 0 else {}
                kinds = {s.get("codec_type") for s in details.get("streams", [])}
                valid = {"video", "audio"} <= kinds and float(details.get("format", {}).get("duration", 0)) > 0
                return self.reply(200 if valid else 422, {"ok": valid, "bytes": files[0].stat().st_size,
                                                         "validation": details})
        except Exception:
            self.reply(500, {"ok": False, "error": "Falha ao validar o download"})
        finally:
            LOCK.release()


if __name__ == "__main__":
    if not PASSWORD:
        raise SystemExit("APP_PASSWORD precisa estar configurada")
    ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "10000"))), Handler).serve_forever()
