"""Conciliação de pagamentos CGU com notas fiscais públicas extraídas do SEI.

Uma cobrança pode conter múltiplas NFs; nunca divide valores apenas por aproximação.
Mantém cobranças não conciliadas como Não classificado.
"""
import datetime as dt
from itertools import combinations


def data_iso(s):
    try: return dt.datetime.strptime(s,'%d/%m/%Y').date()
    except (ValueError, TypeError):return None


def normalizar_cnpj(s):
    return ''.join(x for x in str(s or '') if x.isdigit())


def conciliar_fiscal(cobrancas, notas_sei):
    """Somente composições de valor exato, exclusivas e com evidência fiscal.

    - 1 NF quando instrumento corresponde a número e total.
    - Uma NF âncora mais até 2 notas do tipo complementar no mesmo dia de emissão se a diferença
      for exatamente a soma dessas notas, única, e elas não forem âncoras
      de outras cobranças.
    - Não trata instrumentos sem NF como materiais/serviços por suposição.
    """
    resultado, pendencias_fiscais = [], []
    ocupadas=set()
    notas_index = {i:n for i,n in enumerate(notas_sei)}
    # Pre-reserva notas cujo número corresponde diretamente a uma cobrança:
    # em outro instrumento, não podem ser anexadas por mero fechamento de valor.
    ids_ancora=set()
    for c in cobrancas:
        dt_pag=data_iso(next((d['data'] for d in c['documentos'] if d['tipo']=='OB'),''))
        for i,n in notas_index.items():
            if (n['cnpj']==c['cnpj'] and n['numero']==c['instrumento']
                    and n.get('contrato') in (None,c['contrato'])
                    and dt_pag and data_iso(n['emissao']) and
                    -2 <= (dt_pag-data_iso(n['emissao'])).days <= 430):
                ids_ancora.add(i)

    for c in cobrancas:
        mes=c['mes_pagamento']
        pago = data_iso(next((d['data'] for d in c['documentos'] if d['tipo']=='OB'),''))
        candidatas=[]
        for i,n in notas_index.items():
            emissao=data_iso(n.get('emissao'))
            if (i in ocupadas or n['cnpj']!=c['cnpj'] or
                (n.get('contrato') and n['contrato']!=c['contrato']) or
                not pago or not emissao or not (-2 <= (pago-emissao).days <= 430)):
                continue
            if n['numero']==c['instrumento']:
                candidatas.append((i,n))
        # Se houver notas com numeração homônima, exigir valor único entre candidatas.
        opcoes=[]
        for i,n in candidatas:
            if n['valor_centavos']==c['valor_bruto_centavos']:
                opcoes.append((i,))
            elif n['valor_centavos']<c['valor_bruto_centavos']:
                falta=c['valor_bruto_centavos']-n['valor_centavos']
                mesma_emissao=[]
                for j,outra in notas_index.items():
                    if j==i or j in ocupadas or j in ids_ancora: continue
                    if (outra['cnpj']==c['cnpj'] and outra.get('contrato') in (None,c['contrato'])
                        and outra['tipo_fiscal']!=n['tipo_fiscal'] and outra['emissao']==n['emissao']):
                        mesma_emissao.append((j,outra['valor_centavos']))
                for qtd in range(1,min(2,len(mesma_emissao))+1):
                    for comb in combinations(mesma_emissao,qtd):
                        if sum(v for _,v in comb)==falta:
                            opcoes.append(tuple(sorted([i]+[j for j,_ in comb])))
        # Só aceitar associação se não ambígua.
        opcoes=set(opcoes)
        if len(opcoes)!=1:
            razao = ('Sem NF pública correspondente ou valor fiscal divergente' if not opcoes
                     else 'Várias combinações de notas fiscais possíveis; revisão necessária')
            pendencias_fiscais.append({'cnpj':c['cnpj'],'empresa':c['empresa'],'contrato':c['contrato'],
                  'instrumento':c['instrumento'],'mes_pagamento':mes,
                  'valor_centavos':c['valor_bruto_centavos'],'motivo':razao})
            resultado.append({**c,'numero_nf':None,'tipo_fiscal':None,'documento_sei':None,
                'url_sei':None,'emissao':None,'valor_bruto_centavos':c['valor_bruto_centavos'],
                'categoria':'Não classificado','classificacao':'Cobrança CGU sem conciliação fiscal',
                'tipo_registro':'cobranca','nfs_na_cobranca':0})
            continue
        indices=next(iter(opcoes))
        ocupadas.update(indices)
        nfs=[notas_index[j] for j in indices]
        docs=c['documentos']
        for nf in nfs:
            resultado.append({
                **{k:c[k] for k in ['empresa','cnpj','contrato','instrumento','competencia','mes_pagamento']},
                'numero_nf':nf['numero'],'tipo_fiscal':nf['tipo_fiscal'],
                'documento_sei':nf['documento_sei'],'url_sei':nf.get('url_sei'),
                'emissao':nf['emissao'],'valor_bruto_centavos':nf['valor_centavos'],
                'categoria':nf['categoria'],'classificacao':'Conciliada com PDF público do SEI',
                'tipo_registro':'nota_fiscal', 'nfs_na_cobranca':len(nfs),
                'documentos':docs,'valor_ob_centavos':c['valor_ob_centavos'],
                'valor_dr_centavos':c['valor_dr_centavos'],
                'competencia':nf.get('competencia') or c['competencia'],
            })
    return {'notas':sorted(resultado,key=lambda n:(n['mes_pagamento'],n['cnpj'],n['instrumento'],n['numero_nf'] or '')),
            'pendencias_fiscais':pendencias_fiscais,
            'totais_fiscais':{'notas_conciliadas':sum(x['tipo_registro']=='nota_fiscal' for x in resultado),
                             'cobrancas_sem_nf':len(pendencias_fiscais),
                             'valor_classificado_centavos':sum(x['valor_bruto_centavos'] for x in resultado if x['categoria']!='Não classificado')}}
