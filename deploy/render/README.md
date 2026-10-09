# Teste no Render Free

Este serviço testa o download real de um vídeo público do YouTube, até 480p/50 MB,
valida áudio e vídeo e remove o arquivo. Não substitui ainda a API do Worker nem
entrega o vídeo: primeiro precisamos confirmar que o YouTube aceita esse servidor.

## Publicar

1. Abrir o [Render](https://dashboard.render.com/) e entrar/criar uma conta.
2. Criar um **Web Service**, usando o repositório público
   `https://github.com/mateusartur27/netdownloader` e a branch `codex/youtube-bgutils`.
3. Selecionar Docker, caminho `deploy/render/Dockerfile`, instância **Free**.
4. Adicionar a variável secreta `APP_PASSWORD` com uma senha exclusiva para o teste.
5. Publicar e abrir a URL do serviço. Usuário: `admin`; senha: `APP_PASSWORD`.
6. Testar `https://www.youtube.com/watch?v=jNQXAC9IVRw` e depois
   `https://www.youtube.com/watch?v=waETo-ZWCRw`.

Também é possível usar o Blueprint `render.yaml`, selecionando a mesma branch.
A configuração fixa o plano `free` e solicita `APP_PASSWORD` durante a criação.

Não adicionar forma de pagamento para este teste. Conforme a documentação do
Render, sem forma de pagamento o serviço é suspenso ao atingir a franquia de
tráfego, em vez de cobrar excedentes. O serviço pode dormir após 15 minutos sem
uso, e o primeiro acesso leva aproximadamente um minuto para reativar.

Referências: [Plano gratuito](https://render.com/docs/free) e
[Blueprint](https://render.com/docs/blueprint-spec).

Estado: implementação preparada; publicação no Render e download a partir dele
ainda não foram realizados. A aceitação do IP pelo YouTube não é garantida.

Validação em 8 de outubro de 2026: os três testes HTTP passaram e o container foi
construído no GitHub Actions, com Deno, yt-dlp e ffprobe executados com sucesso.
[Execução 37829603016](https://github.com/mateusartur27/netdownloader/actions/runs/37829603016).

Teste local da autenticação, URLs e diagnóstico:
`python -m unittest discover -s deploy/render -p test_server.py`
