"""Pesquisa Pública SEI-UTFPR: descobre e lê PDFs fiscais públicos (sem login).

Os PDFs são processados em memória e não são publicados no GitHub Pages.
A rotina é best-effort: erros de SEI não devem destruir a base CGU.
"""
from __future__ import annotations

import datetime as dt
import html
import re
import time
from urllib.parse import urljoin, urlparse

import fitz
import requests
from bs4 import BeautifulSoup

from conciliar import dinheiro, norm

HOST = 'sei.utfpr.edu.br'
DOC_PATH = '/sei/modulos/pesquisa/md_pesq_documento_consulta_externa.php'
URL_PATTERN = re.compile(r'(?:https?://sei\.utfpr\.edu\.br)?(?:/sei/modulos/pesquisa/)?md_pesq_documento_consulta_externa\.php\?[\w=&;%.-]+', re.I)
NUM = r'(?:\d{1,3}(?:\.\d{3})*|\d+),\d{2}'


def normalized_cnpj(s):
    return re.sub(r'\D', '', str(s or ''))


def allowed(url, path):
    p = urlparse(url)
    return p.scheme == 'https' and p.hostname == HOST and p.path == path and bool(p.query)


def extrair_linhas_fiscais(pagina_html, url_processo):
    """Recupera URL contida no onclick window.open, não confunde carimbo com NF."""
    soup = BeautifulSoup(pagina_html, 'html.parser')
    encontrados = []
    for tr in soup.find_all('tr'):
        txt = ' '.join(tr.stripped_strings)
        txtnorm = norm(txt)
        if not re.search(r'\b(NOTA\s+FISCAL|NF[\s-]*E|NFS[\s-]*E)\b', txtnorm):
            continue
        if re.search(r'CARIMBO|ATESTE\b|ATESTADO|INFORMACOES\s+SOBRE', txtnorm):
            continue
        # Restrito à linha do documento; não captura números de outras linhas.
        anchors = tr.find_all('a')
        documento_sei = None
        for a in anchors:
            s = a.get_text(' ', strip=True)
            if re.fullmatch(r'\d{6,8}', s):
                documento_sei = s
                break
        if not documento_sei:
            m = re.match(r'\s*(\d{6,8})\b', txt)
            documento_sei = m.group(1) if m else None
        if not documento_sei:
            continue
        urls = []
        for tag in tr.find_all(True):
            for k in ('onclick', 'href', 'data-url', 'data-href'):
                v = tag.attrs.get(k)
                if not isinstance(v, str):
                    continue
                v = html.unescape(v).replace('\\/', '/')
                urls.extend(m.group(0) for m in URL_PATTERN.finditer(v))
        urls = list(dict.fromkeys(urljoin(url_processo, x) for x in urls))
        urls = [u for u in urls if allowed(u, DOC_PATH)]
        if not urls:
            encontrados.append({'documento_sei': documento_sei, 'rotulo_sei': txt[:180], 'url': None})
        else:
            encontrados.append({'documento_sei': documento_sei, 'rotulo_sei': txt[:180], 'url': urls[0]})
    return list({x['documento_sei']: x for x in encontrados}.values())


def parse_pdf(pdf_bytes, meta, cnpj_esperado=None):
    if not pdf_bytes.startswith(b'%PDF-'):
        raise ValueError('resposta não é PDF')
    pdf = fitz.open(stream=pdf_bytes, filetype='pdf')
    if len(pdf) > 8:
        raise ValueError('nota fiscal com páginas demais para processamento automático')
    texto = '\n'.join(p.get_text(sort=True) for p in pdf)
    if len(texto.strip()) < 120:
        raise ValueError('PDF sem texto extraível')
    return parse_texto(texto, meta, cnpj_esperado)


def parse_texto(texto, meta, cnpj_esperado=None):
    """Interpreta dois layouts comprovados: DANFSe nacional e DANFE de materiais.

    Layout desconhecido é rejeitado, evitando classificar PDFs sem fundamento.
    """
    upper = norm(texto)
    if 'DANFSE' in upper or 'NUMERO DA NFS-E' in upper:
        tipo, categoria = 'NFS-e', 'Serviços'
        mt = re.search(r'NUMERO DA NFS-E[^\n]*\n\s*(\d{1,9})\s+(\d\d/\d\d/\d{4})', upper)
        if not mt:
            raise ValueError('não foi possível identificar número e emissão da NFS-e')
        numero, emissao = str(int(mt.group(1))), mt.group(2)
        # Primeiro valor sob o cabeçalho de tributação municipal "Valor do Serviço".
        mt_v = re.search(r'VALOR DO SERVICO[^\n]*\n\s*R\$\s*(' + NUM + r')', upper)
        if not mt_v:
            raise ValueError('valor bruto de NFS-e não identificado')
        v = dinheiro(mt_v.group(1))
        comp = re.search(r'CONTRATO\s*N[.°ºO]*\s*(\d+\s*/\s*\d{4})', upper)
        competencia = re.search(r'\bMES\s+(?:DE\s+)?([A-Z]+)\s+(\d{4})', upper)
        meses = {'JANEIRO':1,'FEVEREIRO':2,'MARCO':3,'ABRIL':4,'MAIO':5,'JUNHO':6,'JULHO':7,'AGOSTO':8,'SETEMBRO':9,'OUTUBRO':10,'NOVEMBRO':11,'DEZEMBRO':12}
        competencia_fmt = None
        if competencia and competencia.group(1) in meses:
            competencia_fmt = f'{meses[competencia.group(1)]:02}/{competencia.group(2)}'
    elif 'DANFE' in upper and ('TOTAL DA NOTA' in upper or 'TOTAL DOS PRODUTOS' in upper):
        tipo, categoria = 'NF-e', 'Materiais'
        mt = re.search(r'\bN[Oº°\.]?\s*(\d{1,9})\s*\n', upper)
        if not mt:
            raise ValueError('número da NF-e não identificado')
        numero = str(int(mt.group(1)))
        # Conferir valor pelo TOTAL DA NOTA e não apenas pela base de ICMS.
        mt_v = re.search(r'TOTAL DA NOTA[^\n]*\n([^\n]+)', upper)
        if not mt_v:
            raise ValueError('total da NF-e não identificado')
        nums = re.findall(NUM, mt_v.group(1))
        if not nums:
            raise ValueError('total da NF-e não é numérico')
        v = dinheiro(nums[-1])
        dates = re.findall(r'\b\d{2}/\d{2}/\d{4}\b', upper)
        if not dates:
            raise ValueError('data da NF-e não identificada')
        emissao = dates[0]
        comp = re.search(r'CONTRATO\s*N[.°ºO]*\s*(\d+\s*/\s*\d{4})', upper)
        competencia_fmt = None
    else:
        raise ValueError('layout fiscal ainda não reconhecido')
    if not v or v <= 0:
        raise ValueError('valor inválido na nota fiscal')
    date = dt.datetime.strptime(emissao, '%d/%m/%Y').date()
    # Dados da empresa podem aparecer na chave de acesso ou no texto corrido.
    encontrado = normalized_cnpj(cnpj_esperado) if cnpj_esperado and (cnpj_esperado in re.sub(r'\D', '', texto)) else None
    if cnpj_esperado and not encontrado:
        raise ValueError('CNPJ do prestador/emitente não coincide com a empresa esperada')
    contrato = None
    if comp:
        partes = comp.group(1).replace(' ','').split('/')
        contrato = f'{int(partes[0])}/{partes[1]}'
    return {
        'documento_sei': meta['documento_sei'], 'rotulo_sei': meta.get('rotulo_sei',''),
        'url_sei': meta.get('url'), 'tipo_fiscal':tipo, 'categoria':categoria,
        'numero':numero, 'emissao':emissao, 'ano_emissao':date.year,
        'valor_centavos':v, 'cnpj':encontrado, 'contrato':contrato,
        'competencia':competencia_fmt,
    }


def buscar_notas(config, years, timeout=30):
    """Retorna notas e diagnóstico. Em indisponibilidade, não interrompe CGU."""
    notas, erros = [], []
    stats = {'processos':0, 'documentos_fiscais_localizados':0, 'pdfs_lidos':0,
             'pdfs_rejeitados':0, 'status':'ok'}
    s = requests.Session()
    s.headers.update({'User-Agent':'UTFPR-Consulta-Publica-Contratos/0.3', 'Accept':'text/html,application/pdf'})
    empresas = {normalized_cnpj(e['cnpj']):e for e in config.get('empresas',[])}
    min_year = min(years)-1
    max_docs = max(1,min(int(config.get('sei_max_pdfs_por_empresa',100)),160))
    for e in config.get('empresas', []):
        cnpj = normalized_cnpj(e['cnpj'])
        for proc in e.get('processos_sei', []):
            url = proc.get('url_publica','')
            if not allowed(url, '/sei/modulos/pesquisa/md_pesq_processo_exibir.php'):
                erros.append(f'Processo SEI de {e["nome"]}: URL pública inválida')
                continue
            try:
                response = s.get(url, timeout=timeout)
                response.raise_for_status()
                if 'html' not in response.headers.get('Content-Type','').lower():
                    raise ValueError('processo não retornou HTML')
                todos = extrair_linhas_fiscais(response.content, url)
                stats['processos'] += 1
                stats['documentos_fiscais_localizados'] += len(todos)
            except (requests.RequestException, ValueError) as exc:
                erros.append(f'Processo SEI {e["nome"]}: {type(exc).__name__}')
                continue
            selecionados = []
            for meta in todos:
                # A data da inclusão aparece na linha e pode anteceder pagamento em exercício seguinte.
                datas = re.findall(r'\b\d{2}/\d{2}/(20\d{2})\b', meta['rotulo_sei'])
                if datas and max(int(y) for y in datas) < min_year:
                    continue
                selecionados.append(meta)
            if len(selecionados) > max_docs:
                erros.append(f'SEI {e["nome"]}: {len(selecionados)} documentos relevantes, limite {max_docs}; revisar abrangência')
                stats['status'] = 'parcial'
                selecionados = selecionados[-max_docs:]
            for meta in selecionados:
                if not meta.get('url'):
                    stats['pdfs_rejeitados'] += 1
                    erros.append(f'SEI {meta["documento_sei"]}: sem URL pública de documento')
                    continue
                try:
                    r = s.get(meta['url'], timeout=timeout, headers={'Referer':url}, stream=True)
                    r.raise_for_status()
                    body = bytearray()
                    for chunk in r.iter_content(32768):
                        body.extend(chunk)
                        if len(body)>12_000_000:
                            raise ValueError('PDF excedeu 12 MB')
                    n = parse_pdf(bytes(body),meta,cnpj)
                    if n['ano_emissao'] < min_year:
                        continue
                    n['empresa'] = e['nome']
                    n['cnpj'] = cnpj
                    n['processo_sei'] = proc.get('numero','')
                    notas.append(n)
                    stats['pdfs_lidos'] += 1
                except (requests.RequestException, ValueError, RuntimeError, fitz.FileDataError) as exc:
                    stats['pdfs_rejeitados'] += 1
                    erros.append(f'SEI {meta["documento_sei"]}: {type(exc).__name__}: {str(exc)[:100]}')
                time.sleep(0.15)
    # Duplicatas documentais: conservar primeiro registro público identificado.
    notas = list({(n['cnpj'],n['tipo_fiscal'],n['numero'],n['ano_emissao'],n['valor_centavos']):n for n in notas}.values())
    if erros or (stats['processos'] and not notas):
        stats['status'] = 'parcial' if notas else 'indisponivel'
        if not notas and stats['processos']:
            erros.append('Nenhuma nota fiscal legível encontrada no(s) processo(s) público(s)')
    return {'notas': sorted(notas,key=lambda r:(r['cnpj'],r['ano_emissao'],r['numero'],r['tipo_fiscal'])),
            'estatisticas': stats, 'erros': erros[:60]}
