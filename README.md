# Gestão de Contratos UTFPR Londrina — PWA v0.2

PWA público com sincronização diária da API CGU, focado em **pagamentos** (sem controle de empenho nesta versão).

## O que mudou

- `scripts/sync.py`: busca apenas **fase 3** (pagamentos), pagina com a chave `CGU_API_KEY` guardada no GitHub Secrets e grava arquivo `data/resumo.json` somente em caso de consulta completa.
- `scripts/conciliar.py`: extrai número do instrumento de cobrança, contrato e competência a partir do campo `observacao`; agrupa OB e DR da mesma empresa + contrato + instrumento; preserva valor bruto e documentos originários. Usa o mês da OB como mês do pagamento. Se faltar OB, não presume mês nem lança a DR no total conciliado.
- `config.json`: cadastro de empresas e classificações **manualmente validadas** por documentos fiscais. Configurados ARCOLON: 7 e 142 como serviços; 289 como materiais. Outros instrumentos ficam `Não classificado`.
- Interface: totais de serviços, materiais, não classificados, pagamentos por mês, agrupamento por nota/instrumento e pendências, com CSV em UTF-8.
- Cache PWA atualizado para v2.

**Atenção:** trata-se de demonstrativo por **instrumento de cobrança**, não de integração com banco de notas fiscais. A correspondência instrumento↔nota e a classificação serviços/materiais são confirmadas apenas para os três documentos conhecidos. O sistema não deduz categoria apenas pela natureza/elemento de despesa e não identifica NF-e automaticamente para outros documentos. Não calcula saldos de empenho. Em caso de documento não original, valor ou data ausentes, ou OB da mesma cobrança em meses diferentes, exige revisão.

## Atualizar seu repositório atual (sem instalação local)

1. Baixe o ZIP e extraia os arquivos.
2. Abra `https://github.com/igorguiz/gestao-contratos-utfpr` e faça upload do conteúdo extraído, mantendo pastas. O GitHub permite substituir arquivos pelo mesmo nome. **Não apague** as configurações existentes em Settings ou o Secret `CGU_API_KEY`.
3. Se a pasta oculta `.github` não subir pelo navegador, **não é necessário alterá-la**: o workflow `sync.yml` atual segue funcional e executa `scripts/sync.py`. Os demais arquivos novos importantes são `scripts/conciliar.py` e `tests/test_conciliar.py`.
4. Confirme o commit na branch `main`.
5. Acesse `Actions → Consultar CGU e publicar PWA → Run workflow` (ou aguarde a execução disparada pelo commit). Verifique conclusão verde.
6. Acesse `https://igorguiz.github.io/gestao-contratos-utfpr/` e recarregue a página (Ctrl+F5, caso apareça interface antiga).

O arquivo `data/resumo.json` no ZIP é um placeholder (sem dados financeiros). O GitHub Actions consulta a CGU e cria a versão preenchida durante a publicação; não é preciso, nem recomendado, inserir chaves de API no repositório.

## Como adicionar empresas e categorias

Em `config.json`, acrescente outro objeto em `empresas`, com nome e CNPJ sem pontuação. A cada inclusão a automação passa a consultar a empresa em 2026. Para classificações confirmadas, acrescente objetos a `classificacoes_validadas` com CNPJ, contrato no formato `18/2022`, número de instrumento e categoria `Serviços` ou `Materiais`. **Não classifique por suposição**.

## Regras e limitações de conciliação

- Valores armazenados em **centavos inteiros** para não ter arredondamentos de ponto flutuante.
- A observação textual CGU pode variar. O parser registra documentos não reconhecidos como pendência em vez de inventar vínculos.
- A soma de OB+DR é aceita quando os documentos compartilham CNPJ, contrato e instrumento, inclusive com datas distintas; se retenção não encontrar OB, fica pendente. Não existe garantia de que agrupamento por observação baste em situações de faturamento parcelado ou múltiplos documentos fiscais com mesmo instrumento.
- Não fazem parte dos totais conciliados: valores ausentes, documentos não originais, retenções isoladas, instrumentos sem identificação ou casos com OB em meses diferentes. Revise os casos pendentes antes de considerar o total de pagamentos completo.
- O total conciliado **não** equivale automaticamente ao total executado no SIAFI. Compare os totais com o Portal e verifique estornos e restituições que podem exigir tratamento adicional.
- A fonte da classificação dos três casos conhecidos são notas fiscais apresentadas e comparadas com documentos CGU. As demais categorias permanecem desconhecidas.
- Os dados publicados no GitHub Pages são públicos. Não inclua arquivos ou campos não públicos na configuração.

## Testes

`python -m unittest discover -s tests -v`

Não exigem internet, chave da CGU nem bibliotecas externas. Testam NF 142 (OB+DR), NF 289 (OB), retenção isolada e cobrança não classificada.
