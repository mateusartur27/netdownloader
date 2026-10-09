"""Search public Internet Archive movies without an API key."""

import argparse
import html
import json
import os
import re
from pathlib import Path
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('query', nargs='?', default=os.environ.get('SEARCH_QUERY', ''))
    args = parser.parse_args()
    words = re.findall(r'\w+', args.query, flags=re.UNICODE)
    if not words or len(args.query) > 200:
        raise ValueError('Digite uma busca entre 1 e 200 caracteres.')
    params = urlencode({
        'q': 'mediatype:movies AND NOT access-restricted-item:true AND (' + ' AND '.join(words) + ')',
        'fl[]': ['identifier', 'title', 'description'],
        'rows': 20, 'output': 'json',
    }, doseq=True)
    request = Request('https://archive.org/advancedsearch.php?' + params,
                      headers={'User-Agent': 'NetDownloader/1.0'})
    with urlopen(request, timeout=60) as response:
        data = json.load(response)
    results = []
    for item in data['response']['docs']:
        identifier = quote(item['identifier'], safe='')
        results.append({'title': item.get('title') or item['identifier'],
                        'url': 'https://archive.org/details/' + identifier,
                        'source': 'archive.org'})
    output = Path('search-results')
    output.mkdir(exist_ok=True)
    (output / 'results.json').write_text(json.dumps({'results': results}, ensure_ascii=False), encoding='utf-8')
    lines = ['# Resultados: ' + html.escape(args.query), '',
             'Copie uma URL para o workflow **Baixar vídeo**. A presença na busca não garante download.', '']
    lines += [f"- [{html.escape(str(item['title'])).replace('[', '').replace(']', '')}]({item['url']})" for item in results]
    summary = '\n'.join(lines) + '\n'
    (output / 'results.md').write_text(summary, encoding='utf-8')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as stream:
            stream.write(summary)
    print(f'Encontrados {len(results)} vídeos.')


if __name__ == '__main__':
    main()
