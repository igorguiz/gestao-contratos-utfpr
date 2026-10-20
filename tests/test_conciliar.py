import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from conciliar import conciliar, extrair
from fiscal import conciliar_fiscal
from sei import extrair_linhas_fiscais, parse_texto

CFG={'empresas':[{'nome':'ARCOLON','cnpj':'82395773000189'}]}
CNPJ='82395773000189'
BASE='PGTO DO(S) INSTR.(S) DE COBRANCA(S) NUM.(S): {}, CONTRATO Nº: 00018/2022, AO(S) MES(ES): {}'

def doc(code,date,val,obs):
    return {'empresa':'ARCOLON','cnpj':CNPJ,'ano':2026,'fase':3,
            'documento':{'documento':'15014815246'+code,'documentoResumido':code,
                         'data':date,'valor':val,'observacao':obs,'especie':'Original'}}

def nf(numero,valor,categoria,emissao,sei):
    return {'numero':numero,'valor_centavos':valor,'categoria':categoria,
        'tipo_fiscal':'NFS-e' if categoria=='Serviços' else 'NF-e',
        'cnpj':CNPJ,'contrato':'18/2022','emissao':emissao,'ano_emissao':2026,
        'documento_sei':sei,'url_sei':'https://sei.utfpr.edu.br/sei/modulos/pesquisa/md_pesq_documento_consulta_externa.php?TESTE',
        'competencia':None}

class Tests(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(extrair(BASE.format('142','03/2026')),
                         {'instrumento':'142','contrato':'18/2022','competencia':'03/2026'})
        self.assertEqual(extrair('RETENCAO SOBRE A NOTA FISCAL 07 - SERVICOS')['instrumento'],'7')

    def test_january_dr_missing_contract_attaches(self):
        docs=[doc('2026OB000228','28/01/2026','13.922,91',BASE.format('07','12/2025')),
              doc('2026DR800004','28/01/2026','583,14','RETENCAO DE 4,02 PCT SOBRE A NOTA FISCAL 07 - SERVICOS')]
        g=conciliar(docs,CFG)
        self.assertEqual(len(g['cobrancas']),1)
        self.assertEqual(g['cobrancas'][0]['valor_bruto_centavos'],1450605)
        self.assertEqual(g['pendencias'],[])
        f=conciliar_fiscal(g['cobrancas'],[nf('7',1450605,'Serviços','21/01/2026','5476495')])
        self.assertEqual(f['totais_fiscais']['notas_conciliadas'],1)
        self.assertEqual(f['notas'][0]['valor_bruto_centavos'],1450605)

    def test_feb_two_invoices_one_ob_with_retention(self):
        docs=[doc('2026OB000999','09/02/2026','14.411,19',BASE.format('39','01/2026')),
              doc('2026DR800011','09/02/2026','587,50','RETENCAO SOBRE A NOTA FISCAL 39')]
        g=conciliar(docs,CFG)
        self.assertEqual(g['cobrancas'][0]['valor_bruto_centavos'],1499869)
        fisc=conciliar_fiscal(g['cobrancas'],[
            nf('39',1450605,'Serviços','03/02/2026','5492599'),
            nf('281',49264,'Materiais','03/02/2026','5492798')])
        self.assertEqual(len(fisc['notas']),2)
        self.assertEqual({n['categoria']:n['valor_bruto_centavos'] for n in fisc['notas']},
                         {'Serviços':1450605,'Materiais':49264})
        self.assertEqual(sum(n['valor_bruto_centavos'] for n in fisc['notas']),1499869)
        self.assertEqual(fisc['pendencias_fiscais'],[])

    def test_aug_material_anchor_plus_service_note(self):
        docs=[doc('2026OB002038','10/08/2026','15.358,95',BASE.format('305','07/2026')),
              doc('2026DR800078','10/08/2026','663,51',BASE.format('305','07/2026'))]
        g=conciliar(docs,CFG)
        self.assertEqual(g['cobrancas'][0]['valor_bruto_centavos'],1602246)
        f=conciliar_fiscal(g['cobrancas'],[
            nf('305',51980,'Materiais','04/08/2026','5878881'),
            nf('255',1550266,'Serviços','04/08/2026','5878873')])
        self.assertEqual(len(f['notas']),2)
        self.assertEqual({n['categoria']:n['valor_bruto_centavos'] for n in f['notas']},
                         {'Serviços':1550266,'Materiais':51980})
        self.assertFalse(f['pendencias_fiscais'])

    def test_ambiguous_complementary_notes_not_assigned(self):
        docs=[doc('2026OB002038','10/08/2026','15.358,95',BASE.format('305','07/2026')),
              doc('2026DR800078','10/08/2026','663,51',BASE.format('305','07/2026'))]
        g=conciliar(docs,CFG)
        f=conciliar_fiscal(g['cobrancas'],[
            nf('305',51980,'Materiais','04/08/2026','5878881'),
            nf('255',1550266,'Serviços','04/08/2026','5878873'),
            nf('777',1550266,'Serviços','04/08/2026','5879999')])
        self.assertEqual(f['notas'][0]['categoria'],'Não classificado')
        self.assertEqual(len(f['pendencias_fiscais']),1)

    def test_april_separate_ob(self):
        docs=[doc('2026OB000853','15/04/2026','15.732,20',BASE.format('142','03/2026')),
              doc('2026DR800035','13/04/2026','677,73','RETENCAO SOBRE PAGTO DO(S) INSTR.(S) DE COBRANCA(S) NUM.(S): 142, CONTRATO Nº: 00018/2022'),
              doc('2026OB000857','15/04/2026','1.860,86',BASE.format('289','03/2026'))]
        g=conciliar(docs,CFG)
        f=conciliar_fiscal(g['cobrancas'],[
           nf('142',1640993,'Serviços','07/04/2026','5600001'),
           nf('289',186086,'Materiais','07/04/2026','5600002')])
        self.assertEqual(sum(n['valor_bruto_centavos'] for n in f['notas']),1827079)
        self.assertEqual(f['totais_fiscais']['notas_conciliadas'],2)
        self.assertEqual(len(f['pendencias_fiscais']),0)

    def test_ambiguous_fiscal_stays_unclassified(self):
        docs=[doc('2026OB000100','10/06/2026','120,00',BASE.format('990','05/2026'))]
        g=conciliar(docs,CFG)
        f=conciliar_fiscal(g['cobrancas'],[])
        self.assertEqual(f['notas'][0]['categoria'],'Não classificado')
        self.assertEqual(f['notas'][0]['valor_bruto_centavos'],12000)
        self.assertEqual(len(f['pendencias_fiscais']),1)

    def test_dr_without_ob_pending(self):
        docs=[doc('2026DR800035','13/04/2026','677,73','RETENCAO SOBRE NOTA FISCAL 142')]
        g=conciliar(docs,CFG)
        self.assertEqual(g['cobrancas'],[])
        self.assertEqual(len(g['pendencias']),1)

    def test_html_discovers_onclick_not_carimbo(self):
        html='''<table><tr><td><a href="javascript:void(0);" onclick="window.open('md_pesq_documento_consulta_externa.php?TOKEN_TESTE123')">5492599</a></td><td>Nota Fiscal 39</td><td>04/02/2026</td></tr>
        <tr><td>5492801</td><td>Carimbo - ateste para nota fiscal / fatura</td></tr></table>'''
        url='https://sei.utfpr.edu.br/sei/modulos/pesquisa/md_pesq_processo_exibir.php?TESTE'
        docs=extrair_linhas_fiscais(html.encode(),url)
        self.assertEqual(len(docs),1)
        self.assertEqual(docs[0]['documento_sei'],'5492599')
        self.assertTrue(docs[0]['url'].startswith('https://sei.utfpr.edu.br/'))

    def test_parse_text_nfse(self):
        texto='''DANFSe v1.0\nNúmero da NFS-e        Competência        Data\n39     03/02/2026       03/02/2026 08:43:45\n82.395.773/0001-89\nValor do Serviço  Deducoes\nR$ 14.506,05\nContrato n.º 18/2022, mês Janeiro 2026'''
        n=parse_texto(texto,{'documento_sei':'5492599'},CNPJ)
        self.assertEqual((n['numero'],n['valor_centavos'],n['categoria']),('39',1450605,'Serviços'))
        self.assertEqual(n['competencia'],'01/2026')

if __name__=='__main__':unittest.main()
