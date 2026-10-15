# Gestão de Contratos — UTFPR Londrina — PWA v0.3

**Objetivo da versão:** apurar os pagamentos brutos da CGU por mês e separá-los em **serviços** e **materiais** somente quando notas fiscais públicas do SEI permitirem conciliação numérica exata. **Não calcula saldo de empenho.**

## Funcionamento

1. O GitHub Actions consulta a API da CGU para os CNPJs da `config.json` (fase 3, UG 150148, exercício configurado).
2. A rotina `scripts/sei.py` acessa as páginas de **Pesquisa Pública** dos processos SEI configurados, identifica linhas de **Nota Fiscal** (ignora carimbos de ateste) e recupera os PDFs públicos a partir dos links `window.open(...)`.
3. Os PDFs são interpretados **em memória** com PyMuPDF; **não são incluídos no site nem no Git**. Para os layouts já validados, lê o número da nota, emissor, emissão, valor bruto, competência e o tipo de documento (DANFSe = serviços; DANFE = materiais).
4. `scripts/conciliar.py` agrupa pagamentos `OB` e retenções `DR`, mesmo quando a DR omite o contrato, desde que exista uma única OB candidata do mesmo instrumento e CNPJ em até 45 dias.
5. `scripts/fiscal.py` cruza os documentos de cobrança com as NFs por CNPJ, contrato, número, data e **fechamento exato de valores**, incluindo a possibilidade de uma única cobrança abranger **NFS-e + NF-e** emitidas no mesmo dia. Correspondências múltiplas, inexistentes ou divergentes continuam **Não classificadas**.
6. O PWA publica totais mensais, tabela de NFs, links para os documentos públicos, pendências e CSV. Dados brutos sem vínculo seguro aparecem em uma seção própria e entram no **total de documentos CGU** sem duplicidade.

## Casos de referência verificados

| Mês de pagamento | Nota fiscal | Natureza | Valor bruto (R$) | Detalhe CGU |
|---|---|---|---:|---|
| Jan/2026 | NF 7 | Serviços | 14.506,05 | OB 13.922,91 + DR 583,14 |
| Fev/2026 | NF 39 | Serviços | 14.506,05 | Mesmo instrumento abrange NF 39 e NF 281 |
| Fev/2026 | NF 281 | Materiais | 492,64 | OB 14.411,19 + DR 587,50 = 14.998,69 |
| Abr/2026 | NF 142 | Serviços | 16.409,93 | OB 15.732,20 + DR 677,73 |
| Abr/2026 | NF 289 | Materiais | 1.860,86 | OB 1.860,86 |

A confirmação desses números não garante que os demais documentos sejam classificados: devem passar pelos mesmos testes. Não tente imputar o número do documento fiscal à cobrança sem validar os valores.

## Atualização no GitHub, sem instalação no computador

1. **Recomendado:** faça um backup da versão atual do repositório (Code → Download ZIP).
2. Extraia o ZIP v0.3 e, no repositório `igorguiz/gestao-contratos-utfpr`, use **Add file → Upload files** para substituir os arquivos. Preserve a estrutura de pastas (`scripts/`, `tests/`, `data/`, `assets/`).
3. **OBRIGATÓRIO:** atualize `.github/workflows/sync.yml` com a cópia deste ZIP. Se o navegador ocultar `.github`, abra o arquivo existente no GitHub, clique em **Edit** (lápis), substitua o conteúdo pelo arquivo v0.3 e salve na branch `main`. Essa mudança instala as bibliotecas descritas em `requirements.txt`. Sem ela o novo código falhará por falta de dependências.
4. **Não altere nem exponha** o GitHub Secret `CGU_API_KEY`. A chave continua acessível somente ao GitHub Actions.
5. Abra **Actions → Consultar CGU e publicar PWA → Run workflow** na branch `main`. Aguarde a conclusão de `Instalar dependências`, `Testar conciliação`, `Sincronizar documentos CGU` e `Publicar`.
6. Acesse `https://igorguiz.github.io/gestao-contratos-utfpr/` e use Ctrl+F5 se aparecer conteúdo em cache. Verifique janeiro, fevereiro e abril de 2026.

**Importante:** a publicação é pública. A rotina coleta **somente notas públicas** e publica os campos financeiros, seus IDs SEI e links públicos, jamais o PDF integral no Pages. Respeite a política institucional de acesso e os limites de consulta. Links do SEI usam parâmetros que podem mudar; a sincronização tenta redescobri-los diariamente.

## Configurar outras empresas/processos

Na `config.json`, adicione mais empresas com CNPJ numérico e contrato; para cada empresa, cadastre um ou mais objetos em `processos_sei` com `numero` e `url_publica` copiado da **Pesquisa Pública do SEI**. Não insira links de documentos privados. O sistema filtra os documentos pelo CNPJ do emitente, exige PDF válido e identifica apenas layouts fiscais reconhecidos.

A rotina examina documentos incluídos no SEI a partir do ano anterior ao menor exercício consultado (permitindo NFs emitidas em 2025 e pagas em 2026), com limite `sei_max_pdfs_por_empresa` (padrão 100, máximo efetivo 160). Se houver muitas notas, ajuste o limite cuidadosamente e monitore os logs: documentos acima do limite podem não ter sido verificados. A lista SEI pode conter documentos de ateste e outros PDFs; eles são ignorados ou reportados, sem pressupor que sejam notas.

## Regras de conservação e limitações

- `Total bruto CGU` = cobranças agrupadas + documentos financeiros pendentes, sem somar NFs novamente à mesma cobrança.
- `Serviços`/`Materiais` = valores das NFs cuja soma coincide **exatamente** com o pagamento bruto da cobrança, com identificação consistente.
- `Não classificados` = cobranças com valor conhecido mas sem conciliação fiscal inequívoca.
- `Documentos pendentes` = lançamentos CGU sem vínculo seguro; são expostos separadamente.
- Uma nota parcialmente paga, retificação, estorno, múltiplas NFs de mesma numeração ou pagamento em várias competências pode exigir tratamento contábil adicional. A rotina é conservadora e não atribui automaticamente categorias em cenários ambíguos.
- A NF-e de materiais e a NFS-e são distinguidas pelo **conteúdo fiscal** (DANFE/DANFSe), não pelo elemento de despesa 339039 nem pela descrição da OB.
- Se o SEI estiver indisponível, a atualização dos documentos CGU ainda poderá ser publicada com o aviso `SEI parcial/indisponível`; cobranças sem documento fiscal serão **Não classificadas**.
- Não calcule saldos de empenhos por estes totais. O saldo a liquidar exige base própria de empenho/reajustes/liquidações.

## Testes e dependências

No workflow GitHub Actions: `python -m pip install -r requirements.txt`, depois `python -m unittest discover -s tests -v`.

O repositório ainda pode manter os workflows de diagnóstico já criados (`testar-sei.yml`, `testar-listagem-sei*.yml`). Eles não são necessários ao PWA v0.3, mas não interferem na atualização principal.
