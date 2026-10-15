"""Sincroniza pagamentos CGU e cria demonstrativo conservador por cobrança e mês."""
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

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / 'config.json').read_text(encoding='utf-8'))
OUT = ROOT / 'data' / 'resumo.json'
API = 'https://api.portaldatransparencia.gov.br/api-de-dados/despesas/documentos-por-favorecido'
KEY = os.environ.get('CGU_API_KEY', '').strip()
YEARS = [int(s.strip()) for s in os.getenv('CGU_YEARS', '2026').split(',') if s.strip()]
MAX_PAGES = int(os.getenv('CGU_MAX_PAGES', '150'))


def request(params):
    req = urllib.request.Request(API + '?' + urllib.parse.urlencode(params), headers={
        'chave-api-dados': KEY, 'Accept': 'application/json', 'User-Agent': 'gestao-contratos-utfpr/0.2'})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=40) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as ex:
            if ex.code not in (429, 500, 502, 503, 504) or attempt == 3:
                raise RuntimeError(f'CGU HTTP {ex.code}: {ex.read(150).decode("utf-8", "replace")}') from None
        except (TimeoutError, urllib.error.URLError):
            if attempt == 3:
                raise
        time.sleep(2 ** attempt * 2)


def payload_lista(d):
    if isinstance(d, list): return d
    if isinstance(d, dict):
        for k in ('data', 'dados', 'content', 'items', 'registros'):
            if isinstance(d.get(k), list): return d[k]
    raise ValueError('Formato da resposta CGU desconhecido')


def main():
    if not KEY:
        raise SystemExit('CGU_API_KEY ausente no GitHub Secrets')
    itens, erros, vistos = [], [], set()
    for e in CONFIG['empresas']:
        for ano in YEARS:
            for pagina in range(1, MAX_PAGES + 1):
                try:
                    documentos = payload_lista(request({'codigoPessoa': e['cnpj'], 'ano': ano, 'fase': 3,
                                                         'ug': CONFIG['ug'], 'pagina': pagina}))
                except Exception as exc:
                    erros.append(f'{e["nome"]}/{ano}/página {pagina}: {exc}')
                    break
                if not documentos:
                    break
                for d in documentos:
                    if not isinstance(d, dict): continue
                    identificador = str(d.get('documento') or d.get('documentoResumido') or '')
                    if not identificador:
                        erros.append(f'{e["nome"]}/{ano}: documento sem identificador')
                        continue
                    identificador = identificador.strip()
                    chave = (str(e['cnpj']), identificador)
                    if chave in vistos: continue
                    vistos.add(chave)
                    itens.append({'empresa': e['nome'], 'cnpj': e['cnpj'], 'ano': ano,
                                  'fase': 3, 'identificador': identificador, 'documento': d})
                if len(documentos) < 15: break
            else:
                erros.append(f'Limite de páginas atingido: {e["nome"]}/{ano}')
    if erros:
        print('\n'.join(erros), file=sys.stderr)
        raise SystemExit(1) # não publica base parcialmente atualizada
    resumo = {'versao': 2, 'atualizado_em': dt.datetime.now(dt.timezone.utc).isoformat(),
              'status': 'ok', 'ug': CONFIG['ug'], 'itens': itens, 'erros': []}
    resumo.update(conciliar(itens, CONFIG))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    temp = OUT.with_suffix('.tmp')
    temp.write_text(json.dumps(resumo, indent=2, ensure_ascii=False), encoding='utf-8')
    temp.replace(OUT)
    print(f'{len(itens)} documentos, {len(resumo["notas"])} cobranças agrupadas, {len(resumo["pendencias"])} pendências')

if __name__ == '__main__':
    main()
