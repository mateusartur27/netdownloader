# Próximo teste: runner em VM gratuita

O computador pessoal não participa da execução. A interface continua no Cloudflare,
e o GitHub Actions mantém a fila, os logs e os artifacts. Uma VM Oracle Cloud Always
Free executa o trabalho de download como self-hosted runner Linux.

## Evidência antes de migrar

Em 8 de outubro de 2026, a execução
[37812712984](https://github.com/mateusartur27/netdownloader/actions/runs/37812712984)
comparou dois vídeos (`waETo-ZWCRw` e `jNQXAC9IVRw`) no mesmo runner público:

| Motor | Versão | Resultado nos dois vídeos |
| --- | --- | --- |
| yt-dlp nightly + BgUtils | 2026.9.27.232945.dev0 + 2.0.2 | Exigência de confirmação de bot, mesmo após gerar token |
| Pytubefix WEB | 11.2.0 | BotDetection antes de listar as faixas |
| YoutubeExplode | 6.6.2 | VideoUnavailableException ao consultar o player Android |

Nenhum produziu mídia válida. A falha do YoutubeExplode não informa explicitamente
a causa; não é possível atribuí-la ao IP com certeza apenas por essa mensagem.
Um MP4 direto já foi baixado e publicado na execução 37807903601.

## Requisitos para testar a VM

1. Conta Oracle Cloud elegível para Always Free. O cadastro e qualquer verificação
   de identidade/cartão precisam ser feitos pelo titular.
2. Criar **somente** uma instância identificada como Always Free, na região da conta.
   Não usar créditos temporários de trial como substituto da gratuidade permanente.
3. Para o primeiro teste, preferir Ubuntu e a shape AMD `VM.Standard.E2.1.Micro`,
   se disponível. Ela é x64, compatível com o Chrome usado no workflow atual.
   Ampere A1 é ARM e exige ajustar navegador/dependências antes de executar o WPC.
4. Verificar na tela de criação a elegibilidade gratuita de compute e armazenamento.
   Não habilitar recursos pagos ou fazer upgrade da conta para obter capacidade.

Referências: [Free Tier](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm)
e [Always Free](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm).
A disponibilidade depende da região. Instâncias ociosas podem ser recuperadas.
O IP de uma VM também pode ser bloqueado pelo YouTube; essa migração é um teste.

## Configurar após obter a VM

1. Usar um usuário Linux sem privilégios de root para executar o runner.
2. Instalar Python 3.12 com pip e venv, Node 22+, git, ffmpeg, Xvfb e Chrome.
   O workflow instala os pacotes Python; o ambiente precisa permitir essa instalação.
3. Em GitHub **Settings > Actions > Runners > New self-hosted runner**, selecionar
   Linux x64 e seguir os comandos oficiais dentro da VM.
4. Adicionar o rótulo `netdownloader` e configurar o runner como serviço.
5. Antes de registrar o runner, restringir o repositório e a execução dos workflows
   a pessoas confiáveis. Um runner persistente não deve executar código de forks
   ou contribuições não revisadas.
6. Criar a variável de Actions `YTDLP_RUNNER=netdownloader`.
7. Executar **Baixar vídeo**, primeiro com o MP4 de controle e depois com um dos
   dois vídeos da comparação. Não usar cookies nem proxy no primeiro teste.

O runner acessa o GitHub por conexão de saída; o aplicativo não precisa de uma
porta de entrada na VM. Remover `YTDLP_RUNNER` retorna os jobs para o runner público.
O ambiente atual da conversa não tem uma VM Oracle nem credenciais de acesso
disponíveis; a criação e o teste dessa infraestrutura ainda não foram realizados.

## Repetir a comparação no Actions

Na branch `codex/youtube-bgutils`, executar o workflow **Baixar vídeo** com
`compare=true` e uma URL pública do YouTube. Ele testa a URL informada e
`jNQXAC9IVRw`, sem duplicar URLs iguais. O artifact `comparison-<run_id>` contém
`report.json` e os logs individuais. O workflow falha se qualquer caso falhar,
mas publica o relatório mesmo assim. A mídia temporária é removida após a
validação; esse modo serve para diagnóstico, não entrega os vídeos ao usuário.
