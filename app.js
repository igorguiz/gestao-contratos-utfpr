'use strict';
const base=new URL('.',location.href),$=id=>document.getElementById(id);
let dados={notas:[],pendencias:[],pendencias_fiscais:[]};
const safe=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const reais=c=>(Number(c||0)/100).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
const docUrl=u=>{try{const p=new URL(u);return p.protocol==='https:'&&p.hostname==='sei.utfpr.edu.br'&&p.pathname.endsWith('md_pesq_documento_consulta_externa.php')?p.href:null}catch{return null}};
const fetchJSON=async path=>{const r=await fetch(new URL(path,base),{cache:'no-store'});if(!r.ok)throw Error(`${path}: HTTP ${r.status}`);return r.json()};
const filtroEmpresa=x=>Boolean($('empresa').value)&&x.cnpj===$('empresa').value;
const filtroData=(x,k)=>{const mes=x[k]||'';return (!$('ano').value||mes.startsWith($('ano').value))&&(!$('mes').value||mes.endsWith('-'+$('mes').value))};
const filtrados=()=>dados.notas.filter(n=>filtroEmpresa(n)&&filtroData(n,'mes_pagamento'));
const pendentes=()=>dados.pendencias.filter(p=>filtroEmpresa(p)&&filtroData(p,'mes'));
const pendFiscal=()=>dados.pendencias_fiscais.filter(n=>filtroEmpresa(n)&&filtroData(n,'mes_pagamento'));
function render(){
  const selecionada=Boolean($('empresa').value);
  $('resultados').hidden=!selecionada;
  $('titulo-relatorio').hidden=!selecionada;
  if(!selecionada)return;
  const notas=filtrados(),pend=pendentes(),pf=pendFiscal();
  const sum=arr=>arr.reduce((s,n)=>s+(Number(n.valor_bruto_centavos||0)),0);
  const serv=sum(notas.filter(n=>n.categoria==='Serviços'));
  const mat=sum(notas.filter(n=>n.categoria==='Materiais'));
  const nc=sum(notas.filter(n=>n.categoria==='Não classificado'));
  const pd=pend.reduce((s,n)=>s+(Number(n.valor_centavos||0)),0);
  $('servicos').textContent=reais(serv);$('materiais').textContent=reais(mat);
  $('outros').textContent=reais(nc);$('pend-total').textContent=reais(pd);$('total').textContent=reais(serv+mat+nc+pd);
  const meses=new Map();const get=k=>{if(!meses.has(k))meses.set(k,{s:0,m:0,u:0,p:0});return meses.get(k)};
  for(const n of notas){const t=get(n.mes_pagamento);t[n.categoria==='Serviços'?'s':n.categoria==='Materiais'?'m':'u']+=Number(n.valor_bruto_centavos||0)}
  for(const p of pend){if(p.mes)get(p.mes).p+=Number(p.valor_centavos||0)}
  $('mensais').innerHTML=[...meses].sort((a,b)=>a[0].localeCompare(b[0])).map(([k,t])=>`<tr><td>${safe(k)}</td><td>${reais(t.s)}</td><td>${reais(t.m)}</td><td>${reais(t.u)}</td><td>${reais(t.p)}</td><td><strong>${reais(t.s+t.m+t.u+t.p)}</strong></td></tr>`).join('')||'<tr><td colspan="6">Nenhum pagamento encontrado.</td></tr>';
  $('notas').innerHTML=notas.map(n=>{
    const isNF=n.tipo_registro==='nota_fiscal',url=docUrl(n.url_sei);
    const rotulo=isNF?`NF ${safe(n.numero_nf)} <small>${safe(n.tipo_fiscal)} · SEI ${safe(n.documento_sei)}</small>`:`Cobrança ${safe(n.instrumento)} <small>Sem NF conciliada</small>`;
    const link=url?`<a href="${safe(url)}" target="_blank" rel="noopener noreferrer">Abrir PDF público no SEI ↗</a>`:'<span class="muted">PDF não identificado</span>';
    return `<tr><td>${safe(n.mes_pagamento)}</td><td>${safe(n.empresa)}<small>${safe(n.contrato)}</small></td>`+
    `<td>${rotulo}</td><td>${safe(n.categoria)}</td><td>${safe(n.emissao||'—')}<small>Comp.: ${safe(n.competencia||'—')}</small></td><td><strong>${reais(n.valor_bruto_centavos)}</strong></td>`+
    `<td>${link}<small>${safe(n.classificacao)}</small><details><summary>Instrumento ${safe(n.instrumento)} · ${n.documentos.length} documento(s) CGU</summary>`+
    n.documentos.map(d=>`<p class="doc">${safe(d.resumido)} · ${safe(d.data)} · ${reais(d.valor_centavos)}</p>`).join('')+
    `</details></td></tr>`;
  }).join('')||'<tr><td colspan="7">Sem notas ou cobranças.</td></tr>';
  $('pend-fiscal-status').textContent=`${pf.length} cobrança(s) sem conciliação fiscal para os filtros atuais.`;
  $('pend-fiscal').innerHTML=pf.map(p=>`<tr><td>${safe(p.mes_pagamento)}</td><td>${safe(p.instrumento)}</td><td>${reais(p.valor_centavos)}</td><td>${safe(p.motivo)}</td></tr>`).join('')||'<tr><td colspan="4">Nenhuma cobrança fiscal pendente.</td></tr>';
  $('pendentes-status').textContent=`${pend.length} documento(s) financeiros pendentes (${reais(pd)}).`;
  $('pendencias').innerHTML=pend.map(p=>`<tr><td>${safe(p.resumido)}</td><td>${safe(p.data)}</td><td>${p.valor_centavos==null?'—':reais(p.valor_centavos)}</td><td>${safe(p.motivo)}</td></tr>`).join('')||'<tr><td colspan="4">Nenhum documento financeiro pendente.</td></tr>';
}
function csv(){
  const cell=v=>'"'+String(v??'').replaceAll('"','""')+'"';
  const header=['empresa','cnpj','contrato','instrumento','nota_fiscal','tipo_fiscal','documento_sei','categoria','emissao','competencia','mes_pagamento','valor_bruto_reais','situacao','url_sei','documentos_cgu'];
  const lines=[header.join(';'),...filtrados().map(n=>[n.empresa,n.cnpj,n.contrato,n.instrumento,n.numero_nf,n.tipo_fiscal,n.documento_sei,n.categoria,n.emissao,n.competencia,n.mes_pagamento,(n.valor_bruto_centavos/100).toFixed(2).replace('.',','),n.classificacao,docUrl(n.url_sei)||'',n.documentos.map(d=>d.resumido).join('|')].map(cell).join(';'))];
  const u=URL.createObjectURL(new Blob(['\ufeff'+lines.join('\r\n')],{type:'text/csv;charset=utf-8'}));
  const a=document.createElement('a');a.href=u;a.download='pagamentos-notas-v03.csv';a.click();setTimeout(()=>URL.revokeObjectURL(u),2000);
}
$('exportar').onclick=csv;['empresa','ano','mes'].forEach(id=>$(id).onchange=render);
Promise.all([fetchJSON('config.json'),fetchJSON('data/resumo.json')]).then(([config,d])=>{
  if(d.versao!==3)throw Error('Arquivo de dados anterior à versão 0.3. Execute a nova sincronização no GitHub Actions.');
  dados=d;
  for(const e of config.empresas){const o=document.createElement('option');o.value=e.cnpj;o.textContent=e.nome+' — '+e.cnpj;$('empresa').append(o)}
  const years=[...new Set(d.notas.map(n=>n.mes_pagamento.slice(0,4)).concat(d.pendencias.map(n=>(n.mes||'').slice(0,4))))].filter(Boolean).sort().reverse();
  for(const y of years){const o=document.createElement('option');o.value=y;o.textContent=y;$('ano').append(o)}
  for(let i=1;i<=12;i++){const o=document.createElement('option');o.value=String(i).padStart(2,'0');o.textContent=new Date(2026,i-1,1).toLocaleString('pt-BR',{month:'long'});$('mes').append(o)}
  const st=d.sei?.estatisticas||{};
  $('status').textContent=`Atualizado: ${new Date(d.atualizado_em).toLocaleString('pt-BR')} · CGU: ${d.itens.length} documentos · SEI: ${st.pdfs_lidos??0} PDFs fiscais lidos (${st.status??'sem diagnóstico'}) · ${d.totais_fiscais.notas_conciliadas} notas pagas conciliadas · ${d.pendencias.length} documentos financeiros pendentes`;
  if(st.status!=='ok'){$('status').classList.add('status-warning')}
  render();
}).catch(e=>{$('status').textContent='Erro ao carregar: '+e.message;$('status').classList.add('status-warning')});
if('serviceWorker' in navigator)navigator.serviceWorker.register(new URL('service-worker.js',base)).catch(()=>{});
