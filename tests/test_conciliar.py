import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from conciliar import conciliar, extrair
CFG={'classificacoes_validadas':[{'cnpj':'82395773000189','contrato':'18/2022','instrumento':'142','categoria':'Serviços'},{'cnpj':'82395773000189','contrato':'18/2022','instrumento':'289','categoria':'Materiais'}]}
CNPJ='82395773000189'
def doc(code,date,val,obs):
    return {'empresa':'ARCOLON','cnpj':CNPJ,'ano':2026,'fase':3,'documento':{'documento':'15014815246'+code,'documentoResumido':code,'data':date,'valor':val,'observacao':obs,'especie':'Original'}}
class Tests(unittest.TestCase):
    def test_parse(self):
        s='PGTO DO(S) INSTR.(S) DE COBRANCA(S) NUM.(S): 142, CONTRATO Nº: 00018/2022, AO(S) MES(ES): 03/2026'
        self.assertEqual(extrair(s),{'instrumento':'142','contrato':'18/2022','competencia':'03/2026'})
    def test_april(self):
        ob142='PGTO DO(S) INSTR.(S) DE COBRANCA(S) NUM.(S): 142, CONTRATO Nº: 00018/2022, AO(S) MES(ES): 03/2026'
        dr142='RETENCAO DE 4,13 PCT SOBRE PGTO DO(S) INSTR.(S) DE COBRANCA(S) NUM.(S): 142, CONTRATO Nº: 00018/2022'
        ob289='PGTO DO(S) INSTR.(S) DE COBRANCA(S) NUM.(S): 289, CONTRATO Nº: 00018/2022'
        x=conciliar([doc('2026OB000853','15/04/2026','15.732,20',ob142),doc('2026DR800035','13/04/2026','677,73',dr142),doc('2026OB000857','15/04/2026','1.860,86',ob289)],CFG)
        self.assertEqual(len(x['notas']),2)
        cats={n['categoria']:n for n in x['notas']}
        self.assertEqual(cats['Serviços']['valor_bruto_centavos'],1640993)
        self.assertEqual(cats['Materiais']['valor_bruto_centavos'],186086)
        self.assertEqual(sum(n['valor_bruto_centavos'] for n in x['notas']),1827079)
        self.assertEqual(len(x['pendencias']),0)
    def test_missing_invoice_stays_unclassified(self):
        obs='PGTO DO(S) INSTR.(S) DE COBRANCA(S) NUM.(S): 990, CONTRATO Nº: 00018/2022'
        self.assertEqual(conciliar([doc('2026OB000100','10/06/2026','120,00',obs)],CFG)['notas'][0]['categoria'],'Não classificado')
    def test_orphan_retention_not_counted(self):
        obs='RETENCAO SOBRE NOTA FISCAL 142, CONTRATO Nº: 00018/2022'
        x=conciliar([doc('2026DR800035','13/04/2026','677,73',obs)],CFG)
        self.assertEqual(x['notas'],[])
        self.assertEqual(len(x['pendencias']),1)
if __name__=='__main__': unittest.main()
