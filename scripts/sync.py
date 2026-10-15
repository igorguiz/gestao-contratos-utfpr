"""Sincronização CGU + documentos fiscais públicos SEI -> resumo v0.3.

Credencial CGU restrita ao GitHub Actions; nenhum PDF é publicado no Pages.
"""
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from conciliar import conciliar
from fiscal import conciliar_fiscal
from sei import buscar_notas

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / 'config.json').read_text(encoding='utf-8'))
OUT = ROOT / 'data' / 'resumo.json'
API = 'https://api.portaldatransparencia.gov.br/api-de-dados/despesas/documentos-por-favorecido'
KEY = os.environ.get('CGU_API_KEY', '').strip()
YEARS = [int(s.strip()) for s in os.getenv('CGU_YEARS', '2026').split(',') if s.strip()]
MAX_PAGES = int(os.getenv('CGU_MAX_PAGES', '150'))


def request(params):
    req = urllib.request.Request(API + '?' + urllib.parse.urlencode(params), headers={
        'chave-api-dados': KEY, 'Accept':'application/json', 'User-Agent':'gestao-contratos-utfpr/0.3'})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=40) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            if exc.code not in (429,500,502,503,504) or attempt==3:
                raise RuntimeError(f'CGU HTTP {exc.code}: {exc.read(150).decode("utf-8","replace")}') from None
        except (TimeoutError,urllib.error.URLError):
            if attempt==3:raise
        time.sleep(2**attempt*2)


def payload_lista(d):
    if isinstance(d,list): return d
    if isinstance(d,dict):
        for k in ('data','dados','content','items','registros'):
            if isinstance(d.get(k),list):return d[k]
    raise ValueError('Formato de dados CGU desconhecido')


def main():
    if not KEY:raise SystemExit('CGU_API_KEY ausente nos secrets GitHub')
    itens, erros, vistos=[],[],set()
    for empresa in CONFIG['empresas']:
        for ano in YEARS:
            for pagina in range(1,MAX_PAGES+1):
                try:
                    documentos=payload_lista(request({'codigoPessoa':empresa['cnpj'], 'ano':ano,
                        'fase':3,'ug':CONFIG['ug'],'pagina':pagina}))
                except Exception as exc:
                    erros.append(f'{empresa["nome"]}/{ano}/página {pagina}: {exc}')
                    break
                if not documentos:break
                for d in documentos:
                    if not isinstance(d,dict):continue
                    ident=str(d.get('documento') or d.get('documentoResumido') or '').strip()
                    if not ident:
                        erros.append(f'{empresa["nome"]}/{ano}: documento sem identificador')
                        continue
                    chave=(str(empresa['cnpj']),ident)
                    if chave in vistos:continue
                    vistos.add(chave)
                    itens.append({'empresa':empresa['nome'],'cnpj':empresa['cnpj'],'ano':ano,
                                  'fase':3,'identificador':ident,'documento':d})
                if len(documentos)<15:break
            else:erros.append(f'Páginas CGU excedidas {empresa["nome"]}/{ano}')
    if erros:
        print('\n'.join(erros),file=sys.stderr)
        raise SystemExit(1)  # Não publica dados CGU parciais

    grupos=conciliar(itens,CONFIG)
    sei=buscar_notas(CONFIG,YEARS)
    fiscal=conciliar_fiscal(grupos['cobrancas'],sei['notas'])
    # Invariantes de conservação contábil: nunca duplicar ou perder valores
    # entre documentos CGU, cobranças e notas fiscais classificadas.
    tot_grupos=sum(c['valor_bruto_centavos'] for c in grupos['cobrancas'])
    tot_nfs=sum(n['valor_bruto_centavos'] for n in fiscal['notas'])
    if tot_grupos!=tot_nfs:
        raise SystemExit(f'Erro de conciliação fiscal: pagamentos {tot_grupos} != notas/cobranças {tot_nfs}')
    # A categoria não altera o total de documentos: apenas sua distribuição.
    resumo={
        'versao':3, 'atualizado_em':dt.datetime.now(dt.timezone.utc).isoformat(),
        'status':'ok' if sei['estatisticas']['status']=='ok' else 'sei_parcial',
        'ug':CONFIG['ug'],'itens':itens,'erros':[],
        'cobrancas':grupos['cobrancas'],'pendencias':grupos['pendencias'],
        'totais':grupos['totais'],
        'notas':fiscal['notas'],'pendencias_fiscais':fiscal['pendencias_fiscais'],
        'totais_fiscais':fiscal['totais_fiscais'],
        'sei':{'estatisticas':sei['estatisticas'],'erros':sei['erros']},
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    temp=OUT.with_suffix('.tmp')
    temp.write_text(json.dumps(resumo,indent=2,ensure_ascii=False),encoding='utf-8')
    temp.replace(OUT)
    print(f'CGU: {len(itens)} documentos / {len(grupos["cobrancas"])} cobranças; ' 
          f'SEI: {len(sei["notas"])} NFs lidas / {sei["estatisticas"]["status"]}; ' 
          f'Conciliação: {fiscal["totais_fiscais"]["notas_conciliadas"]} notas pagas; ' 
          f'{len(grupos["pendencias"])} pagamentos sem agrupamento; '
          f'{len(fiscal["pendencias_fiscais"])} cobranças sem conciliação fiscal')
    if sei['erros']:
        print('Avisos SEI (máx. 10):',*sei['erros'][:10],sep='\n - ',file=sys.stderr)

if __name__=='__main__': main()
