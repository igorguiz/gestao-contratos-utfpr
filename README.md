# Correção v0.3.2 — conciliação cobrança 305

Substituir APENAS `scripts/fiscal.py` do repositório pelo arquivo deste pacote.

Causa: a v0.3.1 só aceitava NFS-e como nota âncora acompanhada de NF-e complementar. A cobrança 305 usa NF-e 305 (materiais, R$ 519,80) como âncora e NFS-e 255 (serviços, R$ 15.502,66) como complemento.

Alteração: a nota complementar pode ser do tipo fiscal oposto ao da âncora, desde que pertença ao mesmo CNPJ, contrato, data de emissão, não seja âncora de outra cobrança, e a soma feche exatamente com a CGU. Continua rejeitando combinações ambíguas.

Testes locais: `PYTHONPATH=scripts python -m unittest discover -s tests -v` na árvore completa do projeto, incluindo `tests/test_conciliar.py` atualizado.

Executar novamente Actions > Consultar CGU e publicar PWA > Run workflow.
O painel deve apresentar em agosto: serviços R$ 15.502,66; materiais R$ 519,80; total R$ 16.022,46. Outubro permanece NF 306, serviço R$ 16.279,16.
