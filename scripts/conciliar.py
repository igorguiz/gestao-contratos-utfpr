"""Conciliação conservadora de documentos de pagamento CGU. Biblioteca padrão."""
import re
import unicodedata
from collections import defaultdict
from decimal import Decimal, InvalidOperation


def dinheiro(v):
    if v is None or v == '':
        return None
    try:
        s = str(v).replace('R$', '').replace(' ', '').strip()
        if ',' in s:
            s = s.replace('.', '').replace(',', '.')
        return int((Decimal(s) * 100).quantize(Decimal('1')))
    except (InvalidOperation, ValueError):
        return None


def norm(s):
    return ''.join(c for c in unicodedata.normalize('NFD', str(s or '').upper()) if unicodedata.category(c) != 'Mn')


def extrair(obs):
    s = norm(obs)
    instrumento = re.search(r'INSTR\.?\s*\(?S?\)?\s*DE\s*COBRANCA\s*\(?S?\)?\s*NUM\.?\s*\(?S?\)?\s*:\s*([0-9]+)', s)
    if not instrumento:
        instrumento = re.search(r'NOTA\s+FISCAL\s*(?:N[Oº.]*)?\s*0*([0-9]+)', s)
    contrato = re.search(r'CONTRATO\s*N[Oº.:]*\s*([0-9]+\s*/\s*[0-9]{4})', s)
    competencia = re.search(r'MES\s*\(?ES\)?\s*:\s*(\d{2}/\d{4})', s)
    return {'instrumento': str(int(instrumento.group(1))) if instrumento else None,
            'contrato': contrato.group(1).replace(' ', '').lstrip('0') if contrato else None,
            'competencia': competencia.group(1) if competencia else None}


def conciliar(itens, configuracao):
    """Agrupa lançamentos CGU por cobrança: OB + DR inclusive quando DR omite contrato.

    Não interpreta cobrança como NF, nem deduz natureza financeira. Os casos com
    contrato ausente só recebem vínculo quando existe uma única OB candidata.
    """
    fontes, grupos = {}, defaultdict(list)
    pendencias, sem_contrato = [], []
    for item in itens:
        if int(item.get('fase', 0)) != 3: continue
        d = item.get('documento') or {}
        codigo = str(d.get('documento') or item.get('identificador') or '').strip()
        resumido = str(d.get('documentoResumido') or codigo[-12:]).strip()
        tipo = re.search(r'(OB|DR)(\d+)$', resumido.upper())
        centavos = dinheiro(d.get('valor'))
        dados = extrair(d.get('observacao'))
        original = norm(d.get('especie')) in ('', 'ORIGINAL', 'NAO SE APLICA')
        cnpj = re.sub(r'\D', '', str(item.get('cnpj', '')))
        data = str(d.get('data') or '')
        mes = f'{data[6:10]}-{data[3:5]}' if re.fullmatch(r'\d{2}/\d{2}/\d{4}', data) else None
        row = {'id':codigo,'resumido':resumido,'empresa':item.get('empresa'),'cnpj':cnpj,
               'data':data,'mes':mes,'tipo':tipo.group(1) if tipo else 'OUTRO',
               'valor_centavos':centavos,'contrato':dados['contrato'],
               'instrumento':dados['instrumento'],'competencia':dados['competencia'],
               'observacao':d.get('observacao',''),'especie':d.get('especie','')}
        if codigo in fontes: continue
        fontes[codigo] = row
        if not tipo or centavos is None or not mes or not original or centavos <= 0 or not dados['instrumento']:
            row['motivo'] = 'Documento não original, valor/data inválidos ou instrumento não identificável'
            pendencias.append(row)
        elif not dados['contrato']:
            sem_contrato.append(row)
        else:
            grupos[(cnpj,dados['contrato'],dados['instrumento'])].append(row)

    # DR de ISS frequentemente descreve "RETENCAO SOBRE A NOTA FISCAL 07",
    # sem citar contrato. Vincular apenas se houver um único grupo com OB do
    # mesmo CNPJ/instrumento e distância de até 45 dias da OB.
    import datetime as dt
    for row in sem_contrato:
        candidatos = []
        for chave, docs in grupos.items():
            if chave[0]!=row['cnpj'] or chave[2]!=row['instrumento']: continue
            for ob in docs:
                if ob['tipo']!='OB':continue
                delta = abs((dt.datetime.strptime(row['data'],'%d/%m/%Y')-dt.datetime.strptime(ob['data'],'%d/%m/%Y')).days)
                if delta<=45:
                    candidatos.append(chave)
                    break
        candidatos=list(dict.fromkeys(candidatos))
        if len(candidatos)==1:
            row['contrato']=candidatos[0][1]
            row['contrato_inferido_de_ob']=True
            grupos[candidatos[0]].append(row)
        else:
            row['motivo']='Contrato omitido e não há OB única correspondente (necessária revisão)'
            pendencias.append(row)

    cobrancas=[]
    for chave,docs in sorted(grupos.items()):
        obs=[x for x in docs if x['tipo']=='OB']
        drs=[x for x in docs if x['tipo']=='DR']
        if not obs:
            for x in docs:
                x['motivo']='Cobrança sem ordem bancária correspondente'
                pendencias.append(x)
            continue
        meses={x['mes'] for x in obs}
        if len(meses)!=1:
            for x in docs:
                x['motivo']='OB de uma cobrança em diferentes meses: possível parcelamento'
                pendencias.append(x)
            continue
        mes=next(iter(meses))
        cobrancas.append({'empresa':docs[0]['empresa'],'cnpj':chave[0],'contrato':chave[1],
            'instrumento':chave[2], 'mes_pagamento':mes,
            'competencia':next((x['competencia'] for x in obs if x['competencia']),None),
            'valor_bruto_centavos':sum(x['valor_centavos'] for x in docs),
            'valor_ob_centavos':sum(x['valor_centavos'] for x in obs),
            'valor_dr_centavos':sum(x['valor_centavos'] for x in drs),
            'documentos':[{'id':x['id'],'resumido':x['resumido'],'data':x['data'],
                           'tipo':x['tipo'],'valor_centavos':x['valor_centavos'],
                           'contrato_inferido_de_ob':x.get('contrato_inferido_de_ob',False)}
                          for x in sorted(docs,key=lambda r:r['id'])]})
    return {'cobrancas':sorted(cobrancas,key=lambda r:(r['mes_pagamento'],r['cnpj'],r['instrumento'])),
            'pendencias':pendencias,
            'totais':{'documentos_pagamento':len(fontes),
                      'documentos_agrupados':sum(len(c['documentos']) for c in cobrancas),
                      'documentos_pendentes':len(pendencias),
                      'valor_pendente_centavos':sum(x.get('valor_centavos') or 0 for x in pendencias)}}
