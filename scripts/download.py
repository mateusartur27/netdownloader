"""Download one public video for the GitHub Actions artifact."""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", nargs="?", default=os.environ.get("VIDEO_URL", ""))
    parser.add_argument("--output-dir", default="downloads")
    args = parser.parse_args()
    url = args.url
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        print("URL HTTPS inválida.", file=sys.stderr)
        return 2

    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    base_command = [
        sys.executable, "-m", "yt_dlp",
        "--no-playlist",
        "--playlist-items", "1",
        "--max-filesize", "400M",
        "--sleep-requests", "1",
        "--sleep-interval", "5",
        "--max-sleep-interval", "10",
        "--retries", "5",
        "--fragment-retries", "5",
        "--js-runtimes", "node",
        "--format", "bv*[height<=1080]+ba/b[height<=1080]/best",
        "--merge-output-format", "mp4",
        "--restrict-filenames",
        "--output", str(output / "%(title).120B-%(id)s.%(ext)s"),
    ]
    proxy = os.environ.get("YT_DLP_PROXY", "").strip()
    if proxy:
        base_command[3:3] = ["--proxy", proxy]

    is_youtube = parsed.hostname == "youtu.be" or parsed.hostname.endswith(".youtube.com")
    attempts = [("clientes padrão do YouTube", ["--no-plugin-dirs"])] \
        if is_youtube else [("extrator padrão", [])]
    browser_path = os.environ.get("YTDLP_BROWSER_PATH", "").strip()
    if is_youtube and browser_path:
        attempts.append(("mweb com PO Token pelo Chromium", [
            "--extractor-args", "youtube:player_client=mweb;fetch_pot=always;pot_trace=true",
            "--extractor-args", f"youtubepot-wpc:browser_path={browser_path}",
        ]))

    result = None
    for number, (label, extra_args) in enumerate(attempts, start=1):
        print(f"Tentativa {number}/{len(attempts)}: {label}", flush=True)
        result = subprocess.run(base_command + extra_args + [url], check=False)
        if result.returncode == 0:
            break
        for pattern in ("*.part", "*.ytdl"):
            for temporary_file in output.glob(pattern):
                temporary_file.unlink(missing_ok=True)
    if result is None or result.returncode:
        return result.returncode if result else 1
    files = [file for file in output.iterdir() if file.is_file()]
    if not files:
        print("Nenhum arquivo foi produzido.", file=sys.stderr)
        return 1
    if sum(file.stat().st_size for file in files) > 450_000_000:
        print("O arquivo final excede o limite de 450 MB.", file=sys.stderr)
        return 1
    print("Arquivo pronto:", *(file.name for file in files), sep="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
