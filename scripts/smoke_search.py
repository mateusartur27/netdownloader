"""Find candidate URLs for the requested real-world smoke test."""

import json
from pathlib import Path

from yt_dlp import YoutubeDL


QUERIES = {
    "ankara_messi": "Ankara Messi gol Getafe 2007",
    "galo_cruzeiro_2012": "Atlético MG Cruzeiro 2012 gols clássico",
    "atari": "Atari 2600 comercial 1982",
    "specific": "maria fumaça São João del Rei Tiradentes 2018",
    "lucia_1": "GTA VI Lucia Caminos official clip",
    "lucia_2": "GTA VI Lucia trailer 1",
    "lucia_3": "GTA VI Lucia trailer 2",
}


def main():
    results = {}
    with YoutubeDL({"extract_flat": True, "quiet": True, "no_warnings": True}) as ydl:
        for key, query in QUERIES.items():
            try:
                info = ydl.extract_info(f"ytsearch5:{query}", download=False)
                entries = list(info.get("entries") or [])
                results[key] = [{
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "duration": item.get("duration"),
                    "url": item.get("url") or f"https://www.youtube.com/watch?v={item.get('id')}",
                } for item in entries]
            except Exception as error:
                results[key] = {"error": str(error)}
            print(f"{key}: {len(results[key]) if isinstance(results[key], list) else 'erro'} resultados", flush=True)
    path = Path("downloads/smoke-search.json")
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Resultados salvos em {path}")


if __name__ == "__main__":
    main()
