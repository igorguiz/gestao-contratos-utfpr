# Restaurar o PWA Gestão de Contratos (pacote completo v0.3.4)

Este ZIP contém a **estrutura integral necessária ao projeto**, e não apenas diferenças.
Inclui ARCOLON (contrato 18/2022) e SOBENO (contrato 20/2023); regras fiscais corrigidas e tela inicial que solicita empresa.

## Publicação no GitHub

1. Abra https://github.com/igorguiz/gestao-contratos-utfpr e entre na branch `main`.
2. Faça uma cópia de segurança da versão atual (Code > Download ZIP) antes de substituir os arquivos.
3. EXTRAIA este ZIP. Envie à **RAIZ** do repositório o conteúdo da pasta extraída, **não a pasta inteira**. Mantenha caminhos como `.github/workflows/sync.yml`, `scripts/`, `tests/`, `assets/`, `data/`.
4. Para substituir arquivos existentes use GitHub **Add file > Upload files** (ou GitHub Desktop). Envie todas as pastas preservando seus caminhos. Confira a lista de arquivos modificados e confirme o commit.
5. Em **Settings > Secrets and variables > Actions**, confirme que o secret `CGU_API_KEY` ainda existe; ele não acompanha o ZIP e não deve ser colocado em arquivo público.
6. Em **Settings > Pages**, use **GitHub Actions** como Source.
7. Em **Actions > Consultar CGU e publicar PWA**, execute **Run workflow** na branch `main` se a publicação não iniciar automaticamente.
8. Confira as etapas de testes, sincronização CGU/SEI e publicação. Abra o site em janela privativa, selecione primeiro ARCOLON e depois SOBENO.

## Notas importantes

- O arquivo `data/resumo.json` é **apenas uma base inicial vazia**. O workflow cria os dados efetivos ao executar; o ZIP não promete dados atualizados.
- Os valores da faixa `Atualizado` serão determinados pela execução real. A chave da CGU fica no secret do GitHub.
- SOBENO só entra quando a cobrança for seguramente vinculada ao contrato 20/2023. Dados sem vínculo podem não aparecer até o diagnóstico.
- O link público do SEI da SOBENO está cadastrado, mas sua acessibilidade e seus PDFs precisam ser confirmados no GitHub Actions.
- Este pacote é uma **reconstrução com base nas cópias locais das versões anteriores**, não uma leitura confirmada do estado atual do seu repositório remoto. Arquivos externos adicionados ao repositório depois dessas versões não estão incluídos.
