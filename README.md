# Gestão de Contratos UTFPR — PWA (MVP 0.1)

Projeto experimental de consulta a documentos **públicos** do Portal da Transparência (CGU). Unidade Gestora inicial: **150148**; empresa inicial **ARCOLON, CNPJ 82.395.773/0001-89**.

## Publicar sem instalar programas

1. Descompacte o ZIP no seu computador (não execute nenhum instalador).
2. No GitHub, abra o repositório e use **Add file → Upload files**. Envie os arquivos e pastas do projeto, preservando a estrutura. Confirme o commit em `main`. Se o upload pela interface não preservar diretórios ocultos (`.github`), crie o arquivo `.github/workflows/sync.yml` manualmente pelo editor web do GitHub.
3. Em **Settings → Secrets and variables → Actions → New repository secret**, crie `CGU_API_KEY` e cole a **chave nova**, sem expô-la em arquivos ou capturas.
4. Em **Settings → Pages → Build and deployment**, escolha **GitHub Actions** como fonte de publicação.
5. Em **Actions → Consultar CGU e publicar PWA → Run workflow**, execute manualmente. Confira logs de erro antes de confiar nos dados.
6. Após execução válida, abra `https://igorguiz.github.io/gestao-contratos-utfpr/`.

## Limitações importantes

- O GitHub Pages e o arquivo JSON publicado são **públicos**: não inclua dados privados, senhas ou relatórios internos.
- A API da CGU usa o Secret `CGU_API_KEY` **somente no GitHub Actions**, nunca no navegador.
- Esta versão exibe documentos brutos; **não calcula valores empenhados nem saldos** até validação dos campos financeiros e vínculos entre documentos.
- A consulta na API pode retornar falhas ou mudar contratos de paginação/campos. O workflow é interrompido caso haja erro, evitando publicar resultados parciais automaticamente.
- O conjunto inicial consulta exercício de 2026. Alterar `CGU_YEARS` no workflow para outros exercícios, se necessário.
- Uma empresa pode ter mais de um contrato; CNPJ + UG não comprova vínculo a um contrato específico.
- O agendamento diário pode atrasar no GitHub Actions; use o horário de última atualização como referência.
- Se a chave exposta em captura anterior ainda estiver ativa, revogue-a e use uma nova.

## Para cadastrar mais empresas

Edite `config.json` e adicione itens em `empresas`, cada um com `nome`, `cnpj` (apenas números) e `contrato` informativo. A consulta automática percorrerá todas as empresas cadastradas.
