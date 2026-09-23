"""Adapt yt-dlp-getpot-wpc 1.1.2 for an ephemeral GitHub Actions runner."""

import sys
from pathlib import Path


def main() -> None:
    candidates = [
        Path(entry) / "yt_dlp_plugins" / "extractor" / "getpot_wpc.py"
        for entry in sys.path if entry
    ]
    plugin_path = next((path for path in candidates if path.is_file()), None)
    if plugin_path is None:
        raise RuntimeError("Plugin yt-dlp-getpot-wpc não foi encontrado.")

    source = plugin_path.read_text(encoding="utf-8")
    if "__version__ = '1.1.2'" not in source:
        raise RuntimeError("Versão inesperada do yt-dlp-getpot-wpc; patch recusado.")
    original = """            headless=False,
            browser_executable_path=browser_executable_path,
            browser_args=browser_args
        )"""
    replacement = """            headless=True,
            browser_executable_path=browser_executable_path,
            browser_args=browser_args,
            sandbox=False,
        )"""
    if original not in source:
        raise RuntimeError("Estrutura inesperada do plugin; patch recusado.")
    plugin_path.write_text(source.replace(original, replacement, 1), encoding="utf-8")
    print("WPC preparado para o runner efêmero:", plugin_path)


if __name__ == "__main__":
    main()
