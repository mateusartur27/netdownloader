"""Download the seven requested examples and record real outcomes."""

import json
import subprocess
import sys
from pathlib import Path


CASES = {
    "ankara_messi": "https://www.youtube.com/watch?v=waETo-ZWCRw",
    "galo_cruzeiro_2012": "https://www.youtube.com/watch?v=l_jC-xrh4PY",
    "atari": "https://www.youtube.com/watch?v=3eJe4tTMZOE",
    "specific": "https://www.youtube.com/watch?v=U_FOc5XuOpQ",
    "lucia_1": "https://www.youtube.com/watch?v=QdBZY2fkU-0",
    "lucia_2": "https://www.youtube.com/watch?v=VQRLujxTm3c",
    "lucia_3": "https://www.youtube.com/watch?v=lKBu0aeJKik",
}


def main() -> int:
    names = sys.argv[1:] or list(CASES)
    results = {}
    for name in names:
        if name not in CASES:
            raise SystemExit(f"Caso desconhecido: {name}")
        url = CASES[name]
        destination = Path("downloads/smoke") / name
        print(f"\n=== {name}: {url} ===", flush=True)
        result = subprocess.run([
            sys.executable, "scripts/download.py", url,
            "--output-dir", str(destination),
        ], check=False)
        files = []
        for file in destination.glob("*"):
            if not file.is_file():
                continue
            probe = subprocess.run([
                "ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type",
                "-of", "json", str(file),
            ], capture_output=True, text=True, check=False)
            details = json.loads(probe.stdout) if probe.returncode == 0 else {}
            files.append({
                "name": file.name,
                "size": file.stat().st_size,
                "duration": float(details.get("format", {}).get("duration", 0)),
                "streams": [stream.get("codec_type") for stream in details.get("streams", [])],
            })
        valid = result.returncode == 0 and len(files) == 1 and files[0]["duration"] > 0 \
            and "video" in files[0]["streams"] and "audio" in files[0]["streams"]
        results[name] = {"url": url, "exit_code": result.returncode, "valid": valid, "files": files}
        report = Path("downloads/smoke-report.json")
        report.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Resultado {name}: {'OK' if valid else 'FALHA'}, {len(files)} arquivo(s)", flush=True)
    return 0 if all(item["valid"] for item in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
