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
    """Sem calcular saldos de NE. Valores em centavos e rastreabilidade por documento."""
    fontes = {}
    grupos = defaultdict(list)
    pendencias = []
    aprovadas = {(str(x['cnpj']).replace('.', '').replace('/', '').replace('-', ''), str(x['contrato']), str(int(x['instrumento']))): x
                for x in configuracao.get('classificacoes_validadas', [])}
    for item in itens:
        if int(item.get('fase', 0)) != 3:
            continue
        d = item.get('documento') or {}
        codigo = str(d.get('documento') or item.get('identificador') or '')
        resumido = str(d.get('documentoResumido') or codigo[-12:])
        tipo = re.search(r'(OB|DR)(\d+)$', resumido.upper())
        centavos = dinheiro(d.get('valor'))
        dados = extrair(d.get('observacao'))
        original = norm(d.get('especie')) in ('', 'ORIGINAL', 'NAO SE APLICA')
        cnpj = re.sub(r'\D', '', str(item.get('cnpj', '')))
        data = str(d.get('data') or '')
        ano_mes = f'{data[6:10]}-{data[3:5]}' if re.fullmatch(r'\d{2}/\d{2}/\d{4}', data) else None
        row = {'id': codigo, 'resumido': resumido, 'empresa': item.get('empresa'), 'cnpj': cnpj,
               'data': data, 'mes': ano_mes, 'tipo': tipo.group(1) if tipo else 'OUTRO',
               'valor_centavos': centavos, 'contrato': dados['contrato'], 'instrumento': dados['instrumento'],
               'competencia': dados['competencia'], 'observacao': d.get('observacao', ''), 'especie': d.get('especie', '')}
        if codigo in fontes:
            continue
        fontes[codigo] = row
        if not tipo or centavos is None or not ano_mes or not original or centavos < 0 or not dados['instrumento'] or not dados['contrato']:
            row['motivo'] = 'Sem identificação segura, valor, data ou documento original positivo; requer revisão'
            pendencias.append(row)
            continue
        chave = (cnpj, dados['contrato'], dados['instrumento'])
        grupos[chave].append(row)
    notas = []
    for chave, docs in sorted(grupos.items()):
        obs = [x for x in docs if x['tipo'] == 'OB']
        drs = [x for x in docs if x['tipo'] == 'DR']
        # Não atribuir retenção isolada a mês de pagamento sem OB; não presumir múltiplas NFs da mesma cobrança.
        if not obs:
            for x in docs:
                x['motivo'] = 'Retenção sem ordem bancária correspondente'
                pendencias.append(x)
            continue
        meses_ob = {x['mes'] for x in obs}
        if len(meses_ob) > 1:
            for x in docs:
                x['motivo'] = 'OB de uma mesma cobrança em meses diferentes: requer conciliação manual'
                pendencias.append(x)
            continue
        n = aprovadas.get(chave)
        categoria = n.get('categoria') if n else 'Não classificado'
        if categoria not in ('Serviços', 'Materiais'):
            categoria = 'Não classificado'
        notas.append({'empresa': docs[0]['empresa'], 'cnpj': chave[0], 'contrato': chave[1],
                      'instrumento': chave[2], 'categoria': categoria,
                      'classificacao': 'Validada por documento fiscal' if n and categoria != 'Não classificado' else 'Pendente de validação documental',
                      'competencia': next((x['competencia'] for x in obs if x['competencia']), None),
                      'mes_pagamento': next(iter(meses_ob)),
                      'valor_bruto_centavos': sum(x['valor_centavos'] for x in docs),
                      'valor_ob_centavos': sum(x['valor_centavos'] for x in obs),
                      'valor_dr_centavos': sum(x['valor_centavos'] for x in drs),
                      'documentos': [{'id': x['id'], 'resumido': x['resumido'], 'data': x['data'],
                                      'tipo': x['tipo'], 'valor_centavos': x['valor_centavos']} for x in sorted(docs, key=lambda r: r['id'])]})
    return {'notas': sorted(notas, key=lambda r: (r['mes_pagamento'], r['cnpj'], r['instrumento'])),
            'pendencias': pendencias, 'totais': {'documentos_pagamento': len(fontes),
             'documentos_conciliados': sum(len(n['documentos']) for n in notas),
             'documentos_pendentes': len(pendencias)}}
