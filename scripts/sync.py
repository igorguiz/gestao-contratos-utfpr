"""Sincronização CGU: armazena documentos sem inferir somatórios financeiros."""
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
OUT = ROOT / "data" / "resumo.json"
API = "https://api.portaldatransparencia.gov.br/api-de-dados/despesas/documentos-por-favorecido"
KEY = os.environ.get("CGU_API_KEY", "").strip()
YEARS = [int(v) for v in os.getenv("CGU_YEARS", str(dt.date.today().year)).split(",") if v.strip()]
MAX_PAGES = int(os.getenv("CGU_MAX_PAGES", "150"))


def request(params):
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"chave-api-dados": KEY, "Accept": "application/json", "User-Agent": "gestao-contratos-utfpr/0.1"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=40) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 3:
                detail = exc.read(200).decode('utf-8', 'replace')
                raise RuntimeError(f"CGU HTTP {exc.code}: {detail}") from None
        except (TimeoutError, urllib.error.URLError):
            if attempt == 3:
                raise
        time.sleep(2 ** attempt * 2)


def normalize_payload(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "dados", "content", "items", "registros"):
            if isinstance(payload.get(key), list):
                return payload[key]
    raise ValueError('Formato de resposta inesperado da CGU')


def main():
    if not KEY:
        raise SystemExit('CGU_API_KEY ausente. Cadastre o Secret no GitHub.')
    output = {"atualizado_em": dt.datetime.now(dt.timezone.utc).isoformat(), "status": "ok", "itens": [], "erros": []}
    seen = set()
    for empresa in CONFIG['empresas']:
        for year in YEARS:
            for fase in (1, 2, 3):
                for pagina in range(1, MAX_PAGES + 1):
                    params = {"codigoPessoa": empresa['cnpj'], "ano": year, "fase": fase, "ug": CONFIG['ug'], "pagina": pagina}
                    try:
                        docs = normalize_payload(request(params))
                    except Exception as exc:
                        output['erros'].append(f"{empresa['nome']} / {year} / fase {fase} / página {pagina}: {exc}")
                        break
                    if not docs:
                        break
                    for doc in docs:
                        identifier = str(doc.get('codigo') or doc.get('numero') or doc.get('numeroDocumento') or doc.get('documentoResumido') or '') if isinstance(doc,dict) else ''
                        uniq = json.dumps([empresa['cnpj'], year, fase, doc], sort_keys=True, ensure_ascii=False, default=str)
                        if uniq in seen:
                            continue
                        seen.add(uniq)
                        output['itens'].append({'empresa':empresa['nome'],'cnpj':empresa['cnpj'],'ano':year,'fase':fase,'identificador':identifier,'documento':doc})
                    if len(docs) < 15:  # endpoint CGU costuma paginar em 15 registros
                        break
                else:
                    output['erros'].append(f"Limite de {MAX_PAGES} páginas atingido: {empresa['nome']} / {year} / {fase}")
    if output['erros']:
        output['status'] = 'parcial' if output['itens'] else 'erro'
    # Não sobrescrever uma base válida por falha geral de API.
    if output['status'] == 'erro':
        print('\n'.join(output['erros']),file=sys.stderr)
        raise SystemExit(1)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"Gravados {len(output['itens'])} documentos; erros: {len(output['erros'])}")
    if output['erros']:
        print('\n'.join(output['erros']),file=sys.stderr)
        raise SystemExit(1)  # impede publicação automática de base incompleta

if __name__ == '__main__':
    main()
