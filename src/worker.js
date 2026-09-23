import { page } from './page.js';
import { strFromU8, unzipSync } from 'fflate';

const json = (data, status = 200) => new Response(JSON.stringify(data), {
  status,
  headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' },
});

function authorized(request, password) {
  if (!password) return false;
  const value = request.headers.get('authorization') || '';
  if (!value.startsWith('Basic ')) return false;
  try {
    const decoded = atob(value.slice(6));
    const separator = decoded.indexOf(':');
    return separator !== -1 && decoded.slice(0, separator) === 'admin' && decoded.slice(separator + 1) === password;
  } catch {
    return false;
  }
}

function validVideoUrl(value) {
  if (typeof value !== 'string' || value.length > 2000) return null;
  try {
    const url = new URL(value);
    const host = url.hostname.toLowerCase();
    if (url.protocol !== 'https:' || url.username || url.password || url.port ||
        !host.includes('.') || host === 'localhost' || host.endsWith('.local') ||
        /^\d+\.\d+\.\d+\.\d+$/.test(host) || host.includes(':')) return null;
    return url.href;
  } catch {
    return null;
  }
}

function githubPath(env, suffix) {
  const owner = env.GITHUB_OWNER || '';
  const repo = env.GITHUB_REPO || '';
  if (!/^[\w.-]+$/.test(owner) || !/^[\w.-]+$/.test(repo)) throw new Error('Configure GITHUB_OWNER e GITHUB_REPO.');
  return `https://api.github.com/repos/${owner}/${repo}${suffix}`;
}

function githubHeaders(env) {
  if (!env.GITHUB_TOKEN) throw new Error('Configure GITHUB_TOKEN.');
  return {
    authorization: `Bearer ${env.GITHUB_TOKEN}`,
    accept: 'application/vnd.github+json',
    'x-github-api-version': '2026-03-10',
    'user-agent': 'netdownloader-worker',
  };
}

async function github(env, suffix, options = {}) {
  const response = await fetch(githubPath(env, suffix), {
    ...options,
    headers: { ...githubHeaders(env), ...options.headers },
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`GitHub ${response.status}: ${body.slice(0, 300)}`);
  }
  return response;
}

async function searchWeb(query, env) {
  if (!env.BRAVE_API_KEY) return json({ error: 'Configure BRAVE_API_KEY no Worker.' }, 503);
  if (!query || query.length > 200) return json({ error: 'Digite uma busca de até 200 caracteres.' }, 400);
  const params = new URLSearchParams({ q: query, count: '20', safesearch: 'moderate' });
  const response = await fetch(`https://api.search.brave.com/res/v1/videos/search?${params}`, {
    headers: { 'x-subscription-token': env.BRAVE_API_KEY, accept: 'application/json' },
  });
  if (!response.ok) return json({ error: `A busca falhou (Brave ${response.status}). Confira a chave e o plano da API.` }, 502);
  const data = await response.json();
  return json({ results: (data.results || []).map(item => ({
    title: item.title || 'Vídeo sem título',
    url: item.url,
    description: item.description || '',
    thumbnail: item.thumbnail?.src || '',
    duration: item.video?.duration || '',
    source: item.meta_url?.hostname || '',
  })).filter(item => validVideoUrl(item.url)) });
}

async function searchYouTube(query, env) {
  if (!env.GITHUB_REF || !/^[\w./-]+$/.test(env.GITHUB_REF)) return json({ error: 'Configure GITHUB_REF.' }, 503);
  const response = await github(env, '/actions/workflows/search.yml/dispatches', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ ref: env.GITHUB_REF, inputs: { query } }),
  });
  const data = await response.json();
  if (!Number.isSafeInteger(data.workflow_run_id)) throw new Error('GitHub não retornou o ID da busca.');
  return json({ id: data.workflow_run_id, status: 'queued', github_url: data.html_url }, 202);
}

async function startSearch(request, env) {
  let input;
  try { input = await request.json(); } catch { return json({ error: 'JSON inválido.' }, 400); }
  const query = typeof input?.q === 'string' ? input.q.trim() : '';
  if (!query || query.length > 200) return json({ error: 'Digite uma busca de até 200 caracteres.' }, 400);
  if (input.source === 'web') return searchWeb(query, env);
  if (!input.source || input.source === 'youtube') return searchYouTube(query, env);
  return json({ error: 'Fonte de busca inválida.' }, 400);
}

async function createJob(request, env) {
  let input;
  try { input = await request.json(); } catch { return json({ error: 'JSON inválido.' }, 400); }
  const url = validVideoUrl(input?.url);
  if (!url) return json({ error: 'Informe uma URL HTTPS pública de um vídeo.' }, 400);
  if (!env.GITHUB_REF || !/^[\w./-]+$/.test(env.GITHUB_REF)) return json({ error: 'Configure GITHUB_REF.' }, 503);
  const response = await github(env, '/actions/workflows/download.yml/dispatches', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ ref: env.GITHUB_REF, inputs: { url } }),
  });
  const data = await response.json();
  if (!Number.isSafeInteger(data.workflow_run_id)) throw new Error('GitHub não retornou o ID da execução.');
  return json({ id: data.workflow_run_id, status: 'queued', github_url: data.html_url }, 202);
}

async function getRun(id, env, workflow = 'download.yml') {
  const response = await github(env, `/actions/runs/${id}`);
  const run = await response.json();
  return run.event === 'workflow_dispatch' && run.path?.includes(`/${workflow}@`) ? run : null;
}

async function getArtifact(id, env, name = 'video') {
  const artifacts = await (await github(env, `/actions/runs/${id}/artifacts`)).json();
  return artifacts.artifacts?.find(item => item.name === name && !item.expired) || null;
}

async function getSearchJob(id, env) {
  const run = await getRun(id, env, 'search.yml');
  if (!run) return json({ error: 'Busca não encontrada.' }, 404);
  if (run.status !== 'completed') return json({ id, status: run.status, github_url: run.html_url });
  if (run.conclusion !== 'success') return json({ id, status: run.status, conclusion: run.conclusion, github_url: run.html_url });
  const artifact = await getArtifact(id, env, 'search-results');
  if (!artifact) return json({ error: 'Resultados expirados ou indisponíveis.' }, 404);
  const archiveResponse = await fetch(githubPath(env, `/actions/artifacts/${artifact.id}/zip`), {
    headers: githubHeaders(env), redirect: 'manual',
  });
  const location = archiveResponse.headers.get('location');
  if (archiveResponse.status !== 302 || !location?.startsWith('https://')) throw new Error('GitHub não forneceu os resultados da busca.');
  const archive = await fetch(location);
  if (!archive.ok) throw new Error(`Falha ao ler resultados da busca (${archive.status}).`);
  const bytes = new Uint8Array(await archive.arrayBuffer());
  if (bytes.byteLength > 1_000_000) throw new Error('Resultados da busca excederam o limite de tamanho.');
  const files = unzipSync(bytes);
  const name = Object.keys(files).find(key => key.endsWith('results.json'));
  if (!name) throw new Error('Artifact da busca não contém resultados.');
  const data = JSON.parse(strFromU8(files[name]));
  return json({ id, status: 'completed', conclusion: 'success', github_url: run.html_url,
    results: (data.results || []).filter(item => validVideoUrl(item.url)).slice(0, 20) });
}

async function getJob(id, env) {
  const run = await getRun(id, env);
  if (!run) return json({ error: 'Execução não encontrada.' }, 404);
  const artifact = run.status === 'completed' && run.conclusion === 'success'
    ? await getArtifact(id, env) : null;
  return json({ id: run.id, status: run.status, conclusion: run.conclusion, github_url: run.html_url,
    artifact: artifact ? { size: artifact.size_in_bytes, download_url: `/api/jobs/${id}/file` } : null });
}

async function getFile(id, env) {
  const run = await getRun(id, env);
  if (!run) return json({ error: 'Execução não encontrada.' }, 404);
  const artifact = run.status === 'completed' && run.conclusion === 'success'
    ? await getArtifact(id, env) : null;
  if (!artifact) return json({ error: 'Arquivo ainda não disponível ou expirado.' }, 404);
  const githubResponse = await fetch(githubPath(env, `/actions/artifacts/${artifact.id}/zip`), {
    headers: githubHeaders(env), redirect: 'manual',
  });
  const location = githubResponse.headers.get('location');
  if (githubResponse.status !== 302 || !location?.startsWith('https://')) return json({ error: 'GitHub não forneceu o download.' }, 502);
  return new Response(null, { status: 302, headers: { location, 'cache-control': 'no-store' } });
}

export default {
  async fetch(request, env) {
    if (!authorized(request, env.APP_PASSWORD)) {
      return new Response('Autenticação necessária.', { status: 401,
        headers: { 'www-authenticate': 'Basic realm="netdownloader"', 'cache-control': 'no-store' } });
    }
    const url = new URL(request.url);
    try {
      if (request.method === 'GET' && url.pathname === '/') return new Response(page, {
        headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store',
          'content-security-policy': "default-src 'self'; img-src 'self' https: data:; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; base-uri 'none'; form-action 'self'" },
      });
      if (request.method === 'POST' && url.pathname === '/api/search') return startSearch(request, env);
      if (request.method === 'POST' && url.pathname === '/api/jobs') return createJob(request, env);
      const searchMatch = url.pathname.match(/^\/api\/search\/jobs\/([1-9]\d*)$/);
      if (request.method === 'GET' && searchMatch) {
        const id = Number(searchMatch[1]);
        if (!Number.isSafeInteger(id)) return json({ error: 'ID inválido.' }, 400);
        return getSearchJob(id, env);
      }
      const jobMatch = url.pathname.match(/^\/api\/jobs\/([1-9]\d*)(\/file)?$/);
      if (request.method === 'GET' && jobMatch) {
        const id = Number(jobMatch[1]);
        if (!Number.isSafeInteger(id)) return json({ error: 'ID inválido.' }, 400);
        return jobMatch[2] ? getFile(id, env) : getJob(id, env);
      }
      return json({ error: 'Rota não encontrada.' }, 404);
    } catch (error) {
      console.error(error);
      return json({ error: error.message || 'Erro inesperado.' }, 502);
    }
  },
};

export { validVideoUrl };
