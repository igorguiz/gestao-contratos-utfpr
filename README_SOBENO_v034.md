# Atualização v0.3.4 — inclusão SOBENO (contrato 20/2023)

## Arquivos a substituir no repositório (preservar os demais)
- `config.json` — mantém ARCOLON; adiciona SOBENO CNPJ 25.201.004/0001-69, contrato 20/2023, SEI público enviado e UG global 150148.
- `scripts/sync.py` — filtra **apenas** os documentos conciliados da SOBENO ao contrato 20/2023, depois de vincular OB/DR; conserva regras de ARCOLON.

**Não substitua** `scripts/sei.py`, `scripts/fiscal.py`, `scripts/conciliar.py`, `app.js`, `index.html`, `service-worker.js` ou qualquer arquivo da versão atual. Em especial, mantenha a correção v0.3.2 do fiscal e a interface v0.3.3.

1. No GitHub, substitua os dois arquivos listados preservando os caminhos.
2. Confirme alterações em `main`.
3. Em Actions, execute `Consultar CGU e publicar PWA` e confira logs de CGU/SEI.
4. Abra a página em janela privada, selecione SOBENO e confira as notas classificadas, cobranças sem NF e totais.

### Limitações a verificar
- O URL SEI foi cadastrado **tal como fornecido**, mas não foi possível consultar seu HTML neste ambiente. A execução do Actions verificará acessibilidade, presença de PDFs fiscais e layout.
- O número SEI do processo não foi informado; o campo `numero` está vazio, sem inventar identificador.
- A CGU filtra inicialmente por favorecido/CNPJ e UG, não por contrato. Cobranças do CNPJ cujo campo contratual difira de `20/2023` são excluídas do painel SOBENO; documentos sem contrato identificável também não são atribuídos. Confirme as observações para eventual necessidade de regras específicas.
- `CGU_YEARS` permanece `2026` no workflow atual. A faixa de atualização permanece baseada no resultado real da sincronização.
- Se a SOBENO emitir notas em layout diferente do reconhecido, o painel mostrará pagamentos não classificados até aperfeiçoar o extrator.
