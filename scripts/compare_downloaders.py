"""Compare three download engines on the same runner, preserving evidence."""
import importlib.metadata
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def execute(command, log, timeout=240):
    with log.open("w", encoding="utf-8") as handle:
        try:
            return subprocess.run(command, stdout=handle, stderr=subprocess.STDOUT,
                                  timeout=timeout, check=False).returncode
        except subprocess.TimeoutExpired:
            handle.write("\nTIMEOUT\n")
            return 124


def main():
    root = Path("downloads/comparison")
    root.mkdir(parents=True, exist_ok=True)
    urls = list(dict.fromkeys([os.environ["VIDEO_URL"],
                              "https://www.youtube.com/watch?v=jNQXAC9IVRw"]))
    results = []
    for index, url in enumerate(urls, 1):
        for engine in ("yt-dlp-nightly", "pytubefix", "youtubeexplode"):
            destination = root / f"{index}-{engine}"
            destination.mkdir()
            log = destination / "download.log"
            if engine == "yt-dlp-nightly":
                command = [sys.executable, "scripts/download.py", url,
                           "--output-dir", str(destination / "media")]
            elif engine == "pytubefix":
                command = [sys.executable, "scripts/pytubefix_probe.py", url,
                           str(destination / "media")]
            else:
                command = ["dotnet", os.environ["YOUTUBE_PROBE_DLL"], url,
                           str(destination / "media")]
            print(f"Comparando {engine}: {url}", flush=True)
            code = execute(command, log)
            media = destination / "media"
            final = None
            if code == 0 and media.exists():
                if engine == "yt-dlp-nightly":
                    files = list(media.iterdir())
                    if len(files) == 1:
                        final = files[0]
                else:
                    videos, audios = list(media.glob("video.*")), list(media.glob("audio.*"))
                    if len(videos) == len(audios) == 1:
                        final = media / "merged.mkv"
                        code = execute(["ffmpeg", "-y", "-i", str(videos[0]), "-i", str(audios[0]),
                                        "-c", "copy", str(final)], destination / "merge.log")
            valid, details = False, {}
            if code == 0 and final and final.exists():
                probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                        "format=duration:stream=codec_type", "-of", "json", str(final)],
                                       capture_output=True, text=True, check=False)
                try:
                    details = json.loads(probe.stdout)
                    kinds = {s.get("codec_type") for s in details.get("streams", [])}
                    valid = probe.returncode == 0 and float(details.get("format", {}).get("duration", 0)) > 0 \
                        and {"audio", "video"} <= kinds
                except (ValueError, TypeError):
                    pass
            message = log.read_text(encoding="utf-8", errors="replace")
            reason = "ok" if valid else "download_failed"
            if not valid:
                if "confirm" in message.lower() and "bot" in message.lower():
                    reason = "bot_check"
                elif "429" in message:
                    reason = "rate_limited"
                elif code == 124:
                    reason = "timeout"
                elif code == 0:
                    reason = "invalid_media"
            results.append(dict(engine=engine, url=url, exit_code=code,
                                valid=valid, reason=reason, probe=details))
            # Keep evidence, not large duplicate media, in the diagnostic artifact.
            if media.exists():
                for file in media.iterdir():
                    if file.is_file():
                        file.unlink()
            (root / "report.json").write_text(json.dumps({
                "versions": {name: importlib.metadata.version(name) for name in ("yt-dlp", "pytubefix")},
                "results": results,
            }, indent=2), encoding="utf-8")
            print(f"Resultado: {reason}", flush=True)
            time.sleep(5)
    summary = "| Motor | URL | Resultado |\n|---|---|---|\n" + "".join(
        f"| {r['engine']} | {r['url']} | {r['reason']} |\n" for r in results)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as handle:
            handle.write(summary)
    return 0 if all(r["valid"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
