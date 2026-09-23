"""Search YouTube via yt-dlp and write compact JSON for a GitHub artifact."""

import argparse
import json
import os
from pathlib import Path

from yt_dlp import YoutubeDL


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="?", default=os.environ.get("SEARCH_QUERY", ""))
    parser.add_argument("--output", default="search-results/results.json")
    args = parser.parse_args()
    query = args.query.strip()
    if not query or len(query) > 200:
        raise ValueError("Busca inválida: use entre 1 e 200 caracteres.")
    options = {
        "extract_flat": True,
        "quiet": True,
        "no_warnings": True,
        "sleep_interval_requests": 1,
        "retries": 5,
    }
    proxy = os.environ.get("YT_DLP_PROXY", "").strip()
    if proxy:
        options["proxy"] = proxy
    with YoutubeDL(options) as ydl:
        data = ydl.extract_info(f"ytsearch20:{query}", download=False)
    results = []
    for entry in data.get("entries") or []:
        video_id = entry.get("id", "")
        if not video_id:
            continue
        results.append({
            "title": entry.get("title") or "Vídeo sem título",
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "description": entry.get("description") or "",
            "thumbnail": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
            "duration": str(entry.get("duration") or ""),
            "source": "youtube.com",
        })
    path = Path(args.output)
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps({"results": results}, ensure_ascii=False), encoding="utf-8")
    print(f"Encontrados {len(results)} vídeos para a busca.")


if __name__ == "__main__":
    main()
