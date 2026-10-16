"""Regressão: DANFSe v2.0 com 'VALOR DA OPERAÇÃO / SERVIÇO'."""
import unittest
from sei import parse_texto

class LayoutDanfseV2(unittest.TestCase):
    def _texto(self, numero, valor, mes, competencia):
        return f'''DANFSe v2.0
CHAVE DE ACESSO DA NFS-e
411370022823957730001890000000000{int(numero):03}26084994194599
NÚMERO DA NFS-e          COMPETÊNCIA DA NFS-e       DATA E HORA DA EMISSÃO DA NFS-e
{numero}                 {competencia}             {competencia} 14:55:06
Prestador: 82.395.773/0001-89
Descrição do Serviço
Manutenção preventiva conforme Contrato n.º 18/2022, mês {mes} 2026
BC ISSQN                  Alíquota Aplicada            ISSQN Apurado
R$ {valor}                4,28 %                      R$ 663,51
VALOR TOTAL DA NFS-e           VALOR DA OPERAÇÃO / SERVIÇO     Desconto Incondicionado
                            R$ {valor}                     -
Total das Retenções (ISSQN / Federais)       VALOR LÍQUIDO DA NFS-e
R$ 663,51                                    R$ 14.839,15
'''
    def test_255(self):
        r=parse_texto(self._texto('255','15.502,66','Julho','04/08/2026'),{'documento_sei':'5878873'},'82395773000189')
        self.assertEqual((r['numero'],r['valor_centavos'],r['categoria'],r['competencia']),('255',1550266,'Serviços','07/2026'))
    def test_306(self):
        r=parse_texto(self._texto('306','16.279,16','Agosto','15/09/2026'),{'documento_sei':'5988425'},'82395773000189')
        self.assertEqual((r['numero'],r['valor_centavos'],r['categoria'],r['competencia']),('306',1627916,'Serviços','08/2026'))
    def test_nao_usar_valor_liquido_sem_bruto(self):
        t=self._texto('255','15.502,66','Julho','04/08/2026')
        t=t.replace('VALOR TOTAL DA NFS-e           VALOR DA OPERAÇÃO / SERVIÇO     Desconto Incondicionado\n                            R$ 15.502,66                     -\n','')
        with self.assertRaisesRegex(ValueError,'valor bruto'):
            parse_texto(t,{'documento_sei':'5878873'},'82395773000189')
if __name__=='__main__': unittest.main()
