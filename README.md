# NetDownloader

Busca vídeos e baixa um vídeo público por solicitação. A interface e a API rodam no Cloudflare Workers. A busca no YouTube e os downloads usam `yt-dlp` no GitHub Actions; a busca em outros sites usa a Brave Video Search, se configurada. O resultado do download é um ZIP com o vídeo, disponível por 1 dia no artifact da execução.

## Preparar

1. Crie um repositório GitHub e envie estes arquivos para a branch padrão. O workflow `.github/workflows/download.yml` precisa estar nessa branch.
2. Crie um **fine-grained personal access token** do GitHub limitado a esse repositório, com permissão **Actions: Read and write**. O Worker usa o token para iniciar execuções, consultar o andamento e gerar links para os arquivos.
3. Para pesquisar vídeos fora do YouTube, crie uma chave da [Brave Video Search API](https://api-dashboard.search.brave.com/documentation/services/video-search). A busca no YouTube e os downloads por URL funcionam sem a Brave. O plano Search custa US$ 5 por 1.000 buscas e inclui US$ 5 de crédito mensal, sujeito às condições atuais da Brave.
4. Edite `GITHUB_OWNER`, `GITHUB_REPO` e `GITHUB_REF` em `wrangler.jsonc`. Instale as dependências com `npm install`.
5. Configure os segredos do Worker:

   ```sh
   npx wrangler secret put APP_PASSWORD
   npx wrangler secret put GITHUB_TOKEN
   ```

   Se quiser pesquisar em outros sites, configure também `npx wrangler secret put BRAVE_API_KEY`.

6. Execute `npm run deploy`. Abra a URL informada pelo Wrangler. O navegador pedirá usuário **admin** e a senha `APP_PASSWORD`.

Para desenvolvimento local, copie `.dev.vars.example` para `.dev.vars`, preencha os valores e execute `npm run dev`. Esse arquivo é ignorado pelo Git.

## API

Todas as rotas exigem autenticação HTTP Basic (`admin:APP_PASSWORD`).

| Rota | Função |
| --- | --- |
| `POST /api/search` com `{"q":"...","source":"youtube"}` | Inicia busca no YouTube via GitHub Actions |
| `POST /api/search` com `{"q":"...","source":"web"}` | Pesquisa na Brave Video Search; exige chave |
| `GET /api/search/jobs/:id` | Consulta uma busca no YouTube e retorna os resultados |
| `POST /api/jobs` com `{"url":"https://..."}` | Inicia um download e retorna o ID da execução |
| `GET /api/jobs/:id` | Consulta andamento e disponibilidade do arquivo |
| `GET /api/jobs/:id/file` | Redireciona para o ZIP do artifact |

## Limites

Cada pedido baixa apenas um vídeo, até 1080p quando disponível. O `yt-dlp` recusa arquivos estimados acima de 400 MB, e o script recusa o resultado final acima de 450 MB. O workflow termina após 30 minutos. A busca encontra URLs, mas não garante que o site permita baixar o vídeo; serviços podem exigir login, bloquear automação ou mudar seu funcionamento. Vídeos com DRM não são suportados. Baixe apenas material para o qual você tem permissão.

O GitHub mantém o vídeo em ZIP e os resultados de busca por 1 dia para reduzir o consumo da cota gratuita de artifacts. A busca no YouTube consome minutos e execuções do GitHub Actions, podendo levar alguns minutos. A senha protege a interface inteira; use uma senha forte e mantenha os tokens como segredos do Worker. Para usar somente o GitHub Actions, execute manualmente os workflows **Buscar no YouTube** e **Baixar vídeo** na aba Actions do repositório.

## Evitar bloqueios dos runners públicos

Os runners públicos do GitHub usam IPs dinâmicos e compartilhados. O projeto serializa todas as pesquisas e downloads em uma única fila, aguarda entre requisições e repete falhas transitórias. Em cada download, o workflow também instala o plugin `bgutil-ytdlp-pot-provider` e inicia a versão 2.0.0 do provedor em Docker vinculada apenas a `127.0.0.1`. Para o YouTube, o downloader tenta primeiro os clientes padrão atuais; se eles falharem, tenta o cliente `mweb` com um token criado automaticamente para aquele vídeo. Nenhuma das opções exige chave, conta ou serviço pago.

O PO Token ajuda nos desafios de origem e nos erros `403` do YouTube. Ele não altera o IP do runner e, portanto, não elimina um bloqueio ou limite `429` aplicado ao endereço compartilhado. Nesses casos, aguarde antes de tentar novamente; muitas tentativas consecutivas podem prolongar o limite.

Para uso frequente, configure um **self-hosted runner** em um computador próprio ou servidor com IP estável:

1. No repositório, abra **Settings > Actions > Runners > New self-hosted runner** e siga os comandos do GitHub.
2. Adicione ao runner o rótulo personalizado `netdownloader`.
3. Instale Python 3.12+, Node 22+, ffmpeg, Docker e curl nessa máquina e confirme que estão disponíveis para o usuário do runner.
4. Em **Settings > Secrets and variables > Actions > Variables**, crie `YTDLP_RUNNER` com o valor `netdownloader`.
5. Restrinja o repositório: mantenha-o privado, não habilite workflows vindos de forks e não adicione gatilhos `pull_request` aos workflows que usam o runner próprio.

Remova a variável `YTDLP_RUNNER` para voltar a usar `ubuntu-latest`. Também é possível criar o secret opcional `YT_DLP_PROXY` com uma URL de proxy HTTP, HTTPS ou SOCKS autorizado. Use um único endereço estável; alternar endereços agressivamente tende a piorar a reputação e os bloqueios.

Cookies de uma conta não são configurados por padrão. Eles podem expirar, precisam corresponder ao IP usado para resolver verificações e podem causar restrições na conta. Adicione cookies somente para material próprio que realmente exija login.

### Operação totalmente na nuvem

Nenhum componente precisa ficar no computador do usuário. A configuração recomendada é:

1. Cloudflare Worker para interface, autenticação e API.
2. GitHub Actions para fila, histórico, estado e artifacts.
3. Uma VM Linux pequena com IP público estável como self-hosted runner.

A VM não precisa expor uma porta pública para o aplicativo: o runner abre uma conexão de saída com o GitHub. Um plano com 1 GB de RAM é suficiente para download e remux comuns; transcodificação pesada pode exigir mais memória e CPU. Instale Ubuntu, Python 3.12+, Node 22+ e ffmpeg, registre o runner com o rótulo `netdownloader` e defina `YTDLP_RUNNER=netdownloader` no repositório.

Uma VM com IP próprio reduz a interferência causada por milhares de usuários compartilhando os runners públicos. O endereço ainda pertence a um datacenter e nenhum provedor pode garantir aceitação permanente pelo YouTube ou por outros sites. A fila, os atrasos e as tentativas deste projeto devem permanecer ativos.

Cloudflare Containers é outra opção totalmente gerenciada, porém requer Workers Paid, usa disco temporário e não fornece por padrão um IP exclusivo para o downloader. Ele simplifica a execução do binário, mas não resolve sozinho a reputação do endereço de saída.

### Operação gratuita

O modo padrão utiliza `ubuntu-latest`. Em repositório público, os runners padrão do GitHub Actions não consomem minutos pagos. O plugin e o provedor de PO Token também são gratuitos e não exigem credenciais. No plano GitHub Free, a cota de artifacts é 500 MB, por isso os vídeos ficam disponíveis por apenas 1 dia e cada resultado final é limitado a 450 MB. Esse modo usa IPs compartilhados e ainda pode sofrer bloqueios ocasionais.

Como alternativa gratuita com um IP menos compartilhado, é possível registrar o runner em uma VM Oracle Cloud Always Free. A opção Ampere A1 oferece gratuitamente até 2 OCPUs e 12 GB de memória no limite documentado atual. Ela exige cadastro na Oracle, depende de capacidade na região escolhida e instâncias consideradas ociosas podem ser recuperadas pela Oracle. Configure essa VM com o mesmo rótulo `netdownloader`; nenhuma parte precisa executar no computador pessoal.

## Testes

`npm test` verifica autenticação, validação de URLs e integração da API com respostas simuladas da Brave e do GitHub.

Para repetir os sete downloads reais do teste de aceitação, use `python scripts/smoke_search.py` para revisar candidatos e `python scripts/smoke_download.py` para baixar e validar os MP4 com `ffprobe`. Os arquivos e relatórios ficam em `downloads/`, fora do Git.
