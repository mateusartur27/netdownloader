import test from 'node:test';
import assert from 'node:assert/strict';
import worker, { validVideoUrl } from '../src/worker.js';
import { page } from '../src/page.js';
import { strToU8, zipSync } from 'fflate';

const env = {
  APP_PASSWORD: 'segredo',
  BRAVE_API_KEY: 'brave-test',
  GITHUB_TOKEN: 'github-test',
  GITHUB_OWNER: 'exemplo',
  GITHUB_REPO: 'netdownloader',
  GITHUB_REF: 'main',
};
const auth = { authorization: `Basic ${btoa('admin:segredo')}` };

function request(path, options = {}) {
  return new Request(`https://example.workers.dev${path}`, {
    ...options,
    headers: { ...auth, ...options.headers },
  });
}

test('protege a interface e a API', async () => {
  const response = await worker.fetch(new Request('https://example.workers.dev/api/jobs/123'), env);
  assert.equal(response.status, 401);
  assert.match(response.headers.get('www-authenticate'), /Basic/);
});

test('script da interface tem sintaxe válida', () => {
  const script = page.match(/<script>([\s\S]*?)<\/script>/)?.[1];
  assert.ok(script);
  assert.doesNotThrow(() => new Function(script));
});

test('rejeita URLs locais, HTTP e credenciais', () => {
  for (const url of ['http://youtube.com/watch?v=1', 'https://localhost/a',
    'https://127.0.0.1/a', 'https://user:pass@example.com/a', 'https://[::1]/a']) {
    assert.equal(validVideoUrl(url), null, url);
  }
  assert.equal(validVideoUrl('https://www.youtube.com/watch?v=1'), 'https://www.youtube.com/watch?v=1');
});

test('busca vídeos e inicia download com o ID retornado pelo GitHub', async () => {
  const originalFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url: String(url), options });
    if (String(url).includes('api.search.brave.com')) return Response.json({ results: [
      { title: 'Vídeo', url: 'https://www.youtube.com/watch?v=abc', thumbnail: { src: 'https://img.example/a.jpg' } },
      { title: 'Inseguro', url: 'http://localhost/video' },
    ] });
    return Response.json({ workflow_run_id: 123, html_url: 'https://github.com/exemplo/netdownloader/actions/runs/123' });
  };
  try {
    const search = await (await worker.fetch(request('/api/search', {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ q: 'video', source: 'web' }),
    }), env)).json();
    assert.equal(search.results.length, 1);
    const response = await worker.fetch(request('/api/jobs', {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ url: search.results[0].url }),
    }), env);
    assert.equal(response.status, 202);
    assert.equal((await response.json()).id, 123);
    assert.equal(calls[1].options.headers['x-github-api-version'], '2026-03-10');
    assert.equal(JSON.parse(calls[1].options.body).inputs.url, 'https://www.youtube.com/watch?v=abc');
  } finally { globalThis.fetch = originalFetch; }
});

test('busca no YouTube sem chave Brave e lê o artifact do GitHub', async () => {
  const originalFetch = globalThis.fetch;
  const noBrave = { ...env, BRAVE_API_KEY: undefined };
  const archive = zipSync({ 'results.json': strToU8(JSON.stringify({ results: [
    { title: 'Messi', url: 'https://www.youtube.com/watch?v=abc' },
  ] })) });
  globalThis.fetch = async url => {
    const path = String(url);
    if (path.endsWith('/actions/workflows/search.yml/dispatches')) return Response.json({ workflow_run_id: 456, html_url: 'https://github.com/run/456' });
    if (path.endsWith('/actions/runs/456')) return Response.json({ id: 456, event: 'workflow_dispatch', path: '.github/workflows/search.yml@main', status: 'completed', conclusion: 'success' });
    if (path.endsWith('/actions/runs/456/artifacts')) return Response.json({ artifacts: [{ id: 88, name: 'search-results', expired: false }] });
    if (path.endsWith('/actions/artifacts/88/zip')) return new Response(null, { status: 302, headers: { location: 'https://signed.example/results.zip' } });
    if (path === 'https://signed.example/results.zip') return new Response(archive);
    throw new Error(path);
  };
  try {
    const start = await worker.fetch(request('/api/search', {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ q: 'Ankara Messi', source: 'youtube' }),
    }), noBrave);
    assert.equal(start.status, 202);
    assert.equal((await start.json()).id, 456);
    const done = await (await worker.fetch(request('/api/search/jobs/456'), noBrave)).json();
    assert.equal(done.results[0].title, 'Messi');
  } finally { globalThis.fetch = originalFetch; }
});

test('acompanha a execução e fornece o artifact correto', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async url => {
    const path = String(url);
    if (path.endsWith('/actions/runs/123')) return Response.json({
      id: 123, event: 'workflow_dispatch', path: '.github/workflows/download.yml@main',
      status: 'completed', conclusion: 'success', html_url: 'https://github.com/run/123',
    });
    if (path.endsWith('/actions/runs/123/artifacts')) return Response.json({ artifacts: [
      { id: 77, name: 'video', expired: false, size_in_bytes: 12345 },
    ] });
    if (path.endsWith('/actions/artifacts/77/zip')) return new Response(null, {
      status: 302, headers: { location: 'https://signed.example/file.zip' },
    });
    throw new Error(path);
  };
  try {
    const status = await (await worker.fetch(request('/api/jobs/123'), env)).json();
    assert.equal(status.artifact.download_url, '/api/jobs/123/file');
    const file = await worker.fetch(request('/api/jobs/123/file'), env);
    assert.equal(file.status, 302);
    assert.equal(file.headers.get('location'), 'https://signed.example/file.zip');
  } finally { globalThis.fetch = originalFetch; }
});
