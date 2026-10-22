#!/usr/bin/env python3
"""Diagnóstico público, somente leitura, das páginas Contratos.gov.br.
Sem credenciais, sem alteração do PWA e sem exigir API privada.
"""
import csv
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE='https://contratos.comprasnet.gov.br'
CONTRATOS=[('ARCOLON','154227','00018/2022'),('SOBENO','226065','00029/2023')]
OUT=Path('diagnostico_comprasnet'); OUT.mkdir(exist_ok=True)
SESSION=requests.Session()
SESSION.headers.update({'User-Agent':'Mozilla/5.0 (compatible; UTFPR-Contratos-Diagnostico/1.0; public-readonly)', 'Accept':'text/html,application/json;q=0.9,*/*;q=0.8','Accept-Language':'pt-BR,pt;q=0.9'})

def norm(s):
    return re.sub(r'\s+',' ',str(s or '')).strip()

def fetch(path):
    url=urljoin(BASE,path)
    try:
        r=SESSION.get(url,timeout=30,allow_redirects=True)
        ctype=r.headers.get('Content-Type','')
        result={'requested_url':url,'final_url':r.url,'status':r.status_code,'content_type':ctype,'bytes':len(r.content),'redirects':[{'status':x.status_code,'url':x.url} for x in r.history]}
        if 'html' in ctype.lower():
            soup=BeautifulSoup(r.content,'html.parser')
            for t in soup(['script','style','noscript']):t.decompose()
            result['title']=norm(soup.title.get_text(' ',strip=True)) if soup.title else None
            result['text_sample']=norm(soup.get_text(' ',strip=True))[:600]
            result['tables']=len(soup.find_all('table'))
            result['login_signals']=bool(re.search(r'entrar com gov\.br|acesso negado|login|sess[aã]o expirada',result['text_sample'],re.I))
            result['_soup']=soup
        else:result['body_sample']=norm(r.text)[:250]
        return result
    except requests.RequestException as e:
        return {'requested_url':url,'error':type(e).__name__+': '+str(e)[:300]}

def parse_table(table):
    rows=[]
    for tr in table.select('tr'):
        row=[norm(x.get_text(' ',strip=True)) for x in tr.find_all(['th','td'],recursive=False)]
        if row and any(row):rows.append(row)
    return rows

def get_tables(soup):
    tables=[]
    for i,tab in enumerate(soup.find_all('table')):
        rows=parse_table(tab)
        if not rows:continue
        ctx=norm(' '.join(tab.find_previous(string=True) or ''))[:100]
        tables.append({'index':i,'preceding_text':ctx,'row_count':len(rows),'rows':rows})
    return tables

def save_csv(path,rows):
    with open(path,'w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f,delimiter=';');w.writerows(rows)

results=[]
for name,cid,numero in CONTRATOS:
    print(f'\n===== {name} contrato={numero} id={cid} =====',flush=True)
    page=fetch(f'/transparencia/contratos/{cid}')
    soup=page.pop('_soup',None)
    record={'empresa':name,'id':cid,'numero':numero,'pagina':page}
    print('Página HTTP:',page.get('status','ERRO'),'tabelas:',page.get('tables','?'),'url final:',page.get('final_url','?'))
    if soup:
        tables=get_tables(soup)
        record['tabelas']= [{'index':x['index'],'preceding_text':x['preceding_text'],'row_count':x['row_count'],'first_rows':x['rows'][:3]} for x in tables]
        for t in tables:
            joined=' '.join(' '.join(row) for row in t['rows'][:4]).lower()
            if ('empenh' in joined or ' a liq' in joined or 'rp inscr' in joined):
                save_csv(OUT/f'{name.lower()}_empenhos.csv',t['rows'])
                print('Tabela candidata EMPENHOS:',len(t['rows']),'linhas')
            if ('fatura' in joined or 'data ateste' in joined or 'data emissão' in joined):
                save_csv(OUT/f'{name.lower()}_faturas.csv',t['rows'])
                print('Tabela candidata FATURAS:',len(t['rows']),'linhas')
        # Guardar apenas dados textuais derivados, sem HTML bruto nem sessões/cookies.
        text=norm(soup.get_text(' ',strip=True))
        record['checagens']={
            'id_contrato_no_html':cid in text,
            'contrato_no_html':numero in text or numero.lstrip('0') in text,
            'cnpj_no_html':('82.395.773/0001-89' if name=='ARCOLON' else '25.201.004/0001-69') in text,
            'ha_empenho_2026': '2026NE000051' in text if name=='ARCOLON' else ('2026NE000058' in text or '2026NE000059' in text),
            'ha_fatura_referencia':('15502,66' in text or '15.502,66' in text or '15502.66' in text) if name=='ARCOLON' else ('3649.20' in text or '3.649,20' in text),
        }
        record['links_relevantes']=[{'texto':norm(a.get_text(' ',strip=True))[:90],'href':a.get('href')} for a in soup.find_all('a',href=True) if re.search(r'fatur|cobran|terceir|empenh',norm(a.get_text(' ',strip=True))+' '+a['href'],re.I)][:15]
        print('Checagens:',record['checagens'])
        print('Links relevantes:',record['links_relevantes'][:3])
    # A listagem pública de instrumentos é distinta da tabela de faturas no detalhe.
    from urllib.parse import urlencode
    path='/transparencia/faturas?'+urlencode({'unidade':'153176','numerocontrato':numero})
    invoices=fetch(path)
    invo_soup=invoices.pop('_soup',None)
    print('Instrumentos HTTP:',invoices.get('status','ERRO'),'tabelas:',invoices.get('tables','?'))
    record['instrumentos']=invoices
    if invo_soup:
        inv_tables=get_tables(invo_soup)
        record['instrumentos_tabelas']=[{'index':t['index'],'row_count':t['row_count'],'first_rows':t['rows'][:3]} for t in inv_tables]
        for t in inv_tables:
            if t['row_count']>1:save_csv(OUT/f'{name.lower()}_instrumentos_tabela{t["index"]}.csv',t['rows'])
    results.append(record)
    time.sleep(1)

(OUT/'resultado.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print('\nRESULTADO:',(OUT/'resultado.json').resolve())
for r in results:
    print(r['empresa'],'pagina',r['pagina'].get('status',r['pagina'].get('error')),'instrumentos',r['instrumentos'].get('status',r['instrumentos'].get('error')))
print('Este teste não confirma pagamentos e não altera qualquer arquivo do PWA.')
