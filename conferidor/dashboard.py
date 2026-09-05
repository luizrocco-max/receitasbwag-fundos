"""Dashboard anual de receita (arquivo HTML único, sem dependências).

Calcula todos os meses do ano com o mesmo motor da conferência e gera uma página
com: indicadores, evolução mensal (BTG x Bradesco), contribuição por instituição
e por fundo, observações (início de recebimento e viradas de taxa, lidas da
configuração) e a tabela fundo x mês.

    python -m conferidor --dashboard --ano 2026 --saida Dashboard_Receita_2026.html
"""

import json
from datetime import date, timedelta

from . import calc, conferir, cvm
from .config import carregar_fundos, inicio_de, mudanca_de

MES = ["", "Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

# Feriados nacionais (bancários) — base ANBIMA. Validado contra a CVM: o número
# de dias úteis calculado bate com os dias publicados em jan–ago/2026.
FERIADOS = {
    (2026, 1, 1), (2026, 2, 16), (2026, 2, 17), (2026, 4, 3), (2026, 4, 21),
    (2026, 5, 1), (2026, 6, 4), (2026, 9, 7), (2026, 10, 12), (2026, 11, 2),
    (2026, 11, 15), (2026, 11, 20), (2026, 12, 25),
    (2027, 1, 1), (2027, 2, 8), (2027, 2, 9), (2027, 3, 26), (2027, 4, 21),
    (2027, 5, 1), (2027, 5, 27), (2027, 9, 7), (2027, 10, 12), (2027, 11, 2),
    (2027, 11, 15), (2027, 11, 20), (2027, 12, 25),
}


def dias_uteis(ano: int, mes: int):
    """Dias úteis do mês (sem sábado, domingo e feriado nacional), como ISO."""
    d = date(ano, mes, 1)
    out = []
    while d.month == mes:
        if d.weekday() < 5 and (d.year, d.month, d.day) not in FERIADOS:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def projetar(ano: int, desde_mes: int, quantos: int = 3, fundos_cfg=None):
    """Projeta a receita dos próximos meses mantendo o PL parado no valor mais
    recente da CVM. Só variam a taxa vigente de cada fundo e os dias úteis do mês.
    Retorna None se não houver PL disponível."""
    fundos_cfg = fundos_cfg or carregar_fundos()
    ref_ano, ref_mes = (ano, desde_mes - 1) if desde_mes > 1 else (ano - 1, 12)
    try:
        serie = cvm.ler_series(f"{ref_ano}{ref_mes:02d}", [f.cnpj for f in fundos_cfg])
    except Exception:
        return None
    pl, data_pl = {}, None
    for f in fundos_cfg:
        s_pl = cvm.serie_pl(serie, f.cnpj)
        if not s_pl:
            continue
        ultimo = max(s_pl)
        pl[f.fundo] = s_pl[ultimo]
        data_pl = max(data_pl or ultimo, ultimo)
    if not pl:
        return None

    labels, dias, btg, brad, total = [], [], [], [], []
    for k in range(quantos):
        m = desde_mes + k
        a, m = (ano + (m - 1) // 12, (m - 1) % 12 + 1)
        du = dias_uteis(a, m)
        soma = {"BTG": 0.0, "BRADESCO": 0.0}
        for f in fundos_cfg:
            if f.fundo not in pl:
                continue
            ini = inicio_de(f.fundo)
            entradas = [(d, pl[f.fundo]) for d in du if not ini or d >= ini]
            if not entradas:
                continue
            mud = mudanca_de(f.fundo)
            comp = (calc.receita_com_mudanca(f, entradas, mud) if mud
                    else calc.receita_liquida(f, [p for _, p in entradas]))
            soma[f.instituicao] += comp.get("liquido") or 0.0
        labels.append(MES[m]); dias.append(len(du))
        btg.append(round(soma["BTG"], 2)); brad.append(round(soma["BRADESCO"], 2))
        total.append(round(soma["BTG"] + soma["BRADESCO"], 2))
    return {"labels": labels, "dias": dias, "btg": btg, "brad": brad,
            "total": total, "data_pl": data_pl}


def coletar(ano: int, ate_mes: int = None):
    """Calcula os meses 1..ate_mes do ano e monta os dados do dashboard.

    Se `ate_mes` não for dado, vai até o mês anterior ao atual (a CVM publica com
    atraso). Para no primeiro mês que não puder ser calculado (ex.: sem dados).
    """
    hoje = date.today()
    if ate_mes is None:
        ate_mes = 12 if hoje.year > ano else max(1, hoje.month - 1)
    fundos_cfg = carregar_fundos()
    por_fundo = {
        f.fundo: {"nome": f.fundo, "inst": f.instituicao, "taxa": f.taxa_gestao,
                  "inicio": inicio_de(f.fundo), "mudanca": mudanca_de(f.fundo),
                  "valores": [], "dias": []}
        for f in fundos_cfg
    }
    meses, labels, dias_mes, erros = [], [], [], []
    for mes in range(1, ate_mes + 1):
        chave = f"{ano}-{mes:02d}"
        try:
            res = conferir.calcular_mes(ano, mes, fundos=fundos_cfg)
        except Exception as e:  # sem dados / sem rede: para aqui
            erros.append({"mes": chave, "erro": repr(e)})
            break
        meses.append(chave)
        labels.append(MES[mes])
        dias_mes.append(max(r["dias"] for r in res))  # janela cheia do mês (dias úteis)
        for r in res:
            v = r["bwag"]
            por_fundo[r["fundo"]]["valores"].append(None if v is None else round(v, 2))
            por_fundo[r["fundo"]]["dias"].append(r["dias"])
    projecao = projetar(ano, len(meses) + 1, 3, fundos_cfg) if meses else None
    return {
        "ano": ano, "meses": meses, "labels": labels, "dias_mes": dias_mes,
        "fundos": list(por_fundo.values()), "projecao": projecao,
        "gerado": hoje.strftime("%d/%m/%Y"), "erros": erros,
    }


def gerar(ano: int, saida: str, ate_mes: int = None, fragmento: bool = False):
    """Gera o HTML do dashboard em `saida`. Retorna (caminho, dados).

    `fragmento=True` omite doctype/html/head/body (para publicar como Artifact);
    o padrão é um documento completo para abrir no navegador.
    """
    dados = coletar(ano, ate_mes)
    corpo = (HEAD + BODY).replace("__DATA__", json.dumps(dados, ensure_ascii=False))
    if fragmento:
        html = corpo
    else:
        html = ('<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width, initial-scale=1">'
                + HEAD + "</head><body>" + BODY.replace("__DATA__", json.dumps(dados, ensure_ascii=False))
                + "</body></html>")
    with open(saida, "w", encoding="utf-8") as f:
        f.write(html)
    return saida, dados


HEAD = r"""<title>Receita BWAG 2026</title>
<meta name="description" content="Evolução mensal e contribuição por fundo da receita de gestão dos fundos exclusivos da BWAG.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
  :root {
    color-scheme: light;
    --bg: #f9f9f7; --surface: #fcfcfb; --card: #f2f4f8;
    --ink: #0b0b0b; --ink-2: #52514e; --muted: #898781;
    --grid: #e1e0d9; --axis: #c3c2b7; --border: rgba(11,11,11,.10);
    --brand: #1f4e78; --s-btg: #2a78d6; --s-brad: #eb6834;
    --neg: #d03b3b; --pos: #006300; --tip-bg: #0b0b0b; --tip-ink: #ffffff;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      color-scheme: dark;
      --bg: #0d0d0d; --surface: #1a1a19; --card: #1f2126;
      --ink: #ffffff; --ink-2: #c3c2b7; --muted: #898781;
      --grid: #2c2c2a; --axis: #383835; --border: rgba(255,255,255,.10);
      --brand: #8fb3d9; --s-btg: #3987e5; --s-brad: #d95926;
      --neg: #e66767; --pos: #0ca30c; --tip-bg: #ffffff; --tip-ink: #0b0b0b;
    }
  }
  :root[data-theme="dark"] {
    color-scheme: dark;
    --bg: #0d0d0d; --surface: #1a1a19; --card: #1f2126;
    --ink: #ffffff; --ink-2: #c3c2b7; --muted: #898781;
    --grid: #2c2c2a; --axis: #383835; --border: rgba(255,255,255,.10);
    --brand: #8fb3d9; --s-btg: #3987e5; --s-brad: #d95926;
    --neg: #e66767; --pos: #0ca30c; --tip-bg: #ffffff; --tip-ink: #0b0b0b;
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--ink);
    font: 400 14px/1.45 "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif; }
  .wrap { max-width: 1120px; margin: 0 auto; padding: 32px 24px 48px; display: grid; gap: 24px; }
  header { display: grid; gap: 4px; }
  .eyebrow { font-size: 11px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: var(--brand); }
  h1 { margin: 0; font-size: 26px; font-weight: 600; letter-spacing: -.01em; text-wrap: balance; }
  .sub { color: var(--ink-2); max-width: 65ch; margin: 0; }
  .kpis { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
  .kpi { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 14px 16px; display: grid; gap: 4px; min-width: 0; align-content: start; }
  .kpi .label { font-size: 12px; color: var(--ink-2); }
  .kpi .value { font-size: 24px; font-weight: 600; letter-spacing: -.01em; line-height: 1.15; white-space: nowrap; }
  .kpi.lead .value { font-size: 34px; }
  .kpi .delta { font-size: 12px; color: var(--ink-2); display: flex; align-items: center; gap: 6px; }
  .kpi .delta.neg { color: var(--neg); } .kpi .delta.pos { color: var(--pos); }
  .kpi .delta .arrow { font-weight: 600; }
  .panel { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 18px 20px; display: grid; gap: 12px; align-content: start; min-width: 0; }
  .panel h2 { margin: 0; font-size: 15px; font-weight: 600; }
  .panel .hint { font-size: 12px; color: var(--muted); margin: 0; }
  .grid-2 { display: grid; grid-template-columns: minmax(0, 3fr) minmax(0, 2fr); gap: 16px; }
  .legend { display: flex; gap: 16px; flex-wrap: wrap; font-size: 12px; color: var(--ink-2); }
  .legend span { display: inline-flex; align-items: center; gap: 6px; }
  .sw { width: 12px; height: 12px; border-radius: 3px; display: inline-block; }
  .sw.btg { background: var(--s-btg); } .sw.brad { background: var(--s-brad); }
  .sw.proj { background: linear-gradient(90deg, var(--s-btg) 0 50%, var(--s-brad) 50% 100%); opacity: .45; }
  .chart .proj { opacity: .45; }
  .chart .sep { stroke: var(--axis); stroke-width: 1; }
  .chart .septxt { fill: var(--muted); font-size: 9.5px; }
  svg.chart { width: 100%; height: auto; display: block; overflow: visible; }
  .chart text { font-family: inherit; font-size: 11px; fill: var(--muted); }
  .chart .lbl { fill: var(--ink-2); font-size: 10px; font-weight: 500; }
  .chart .lbl.hi { fill: var(--ink); font-size: 11px; font-weight: 600; }
  .chart .dd { fill: var(--muted); font-size: 9.5px; }
  .chart .grid { stroke: var(--grid); stroke-width: 1; }
  .chart .axis { stroke: var(--axis); stroke-width: 1; }
  .chart .hit { fill: transparent; cursor: default; outline: none; }
  .chart .hit:focus-visible { stroke: var(--brand); stroke-width: 2; }
  .split { display: grid; gap: 10px; }
  .split .bar { display: flex; height: 18px; gap: 2px; background: var(--surface); }
  .split .seg { height: 100%; }
  .split .seg.btg { background: var(--s-btg); border-radius: 4px 0 0 4px; }
  .split .seg.brad { background: var(--s-brad); border-radius: 0 4px 4px 0; }
  .split .rows { display: grid; gap: 8px; }
  .split .row { display: grid; grid-template-columns: auto 1fr auto auto; gap: 10px; align-items: center; font-size: 13px; }
  .split .row .v { font-weight: 600; font-variant-numeric: tabular-nums; }
  .split .row .p { color: var(--ink-2); font-variant-numeric: tabular-nums; min-width: 4.5ch; text-align: right; }
  .split .note { font-size: 12px; color: var(--muted); }
  .funds { display: grid; gap: 6px; }
  .fund { display: grid; grid-template-columns: minmax(160px, 260px) 1fr 120px 52px; gap: 12px; align-items: center; padding: 3px 6px; border-radius: 6px; outline: none; }
  .fund:hover, .fund:focus-visible { background: var(--card); }
  .fund:focus-visible { box-shadow: inset 0 0 0 2px var(--brand); }
  .fund .n { font-size: 13px; display: flex; align-items: center; gap: 8px; min-width: 0; }
  .fund .n span.t { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .fund .dot { width: 8px; height: 8px; border-radius: 50%; flex: none; }
  .fund .track { height: 14px; display: flex; }
  .fund .fill { height: 100%; border-radius: 0 4px 4px 0; min-width: 2px; }
  .fund .v { font-variant-numeric: tabular-nums; text-align: right; font-size: 13px; }
  .fund .p { font-variant-numeric: tabular-nums; text-align: right; font-size: 12px; color: var(--ink-2); }
  .fill.btg, .dot.btg { background: var(--s-btg); } .fill.brad, .dot.brad { background: var(--s-brad); }
  .tag { flex: none; font-size: 10.5px; color: var(--ink-2); border: 1px solid var(--border); border-radius: 999px; padding: 1px 7px; white-space: nowrap; }
  .obs { margin: 0; padding-left: 18px; display: grid; gap: 6px; font-size: 13px; color: var(--ink-2); }
  .obs b { color: var(--ink); font-weight: 600; }
  .tablewrap { overflow-x: auto; }
  table { border-collapse: collapse; width: 100%; font-size: 12px; font-variant-numeric: tabular-nums; white-space: nowrap; }
  th, td { padding: 6px 8px; text-align: right; border-bottom: 1px solid var(--grid); }
  th { color: var(--ink-2); font-weight: 500; font-size: 11px; letter-spacing: .04em; text-transform: uppercase; }
  th:first-child, td:first-child { text-align: left; position: sticky; left: 0; background: var(--surface); }
  td.i { color: var(--muted); text-align: left; }
  td.na { color: var(--muted); }
  tfoot td { font-weight: 600; border-top: 1px solid var(--axis); border-bottom: 0; }
  tfoot tr.dias td { font-weight: 500; color: var(--ink-2); border-top: 1px solid var(--axis); border-bottom: 1px solid var(--grid); }
  tfoot tr.dias + tr td { border-top: 0; }
  .pd { color: var(--muted); font-size: 10.5px; margin-left: 3px; }
  .tip { position: fixed; z-index: 10; pointer-events: none; background: var(--tip-bg); color: var(--tip-ink); padding: 8px 10px; border-radius: 6px; font-size: 12px; line-height: 1.4; box-shadow: 0 4px 14px rgba(0,0,0,.18); max-width: 280px; }
  .tip[hidden] { display: none; }
  .tip b { font-weight: 600; }
  .tip .r { display: flex; justify-content: space-between; gap: 14px; font-variant-numeric: tabular-nums; }
  footer { font-size: 12px; color: var(--muted); max-width: 80ch; display: grid; gap: 4px; }
  @media (max-width: 820px) {
    .kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .grid-2 { grid-template-columns: 1fr; }
    .fund { grid-template-columns: minmax(120px, 1fr) 1fr 100px 46px; }
    .kpi.lead .value { font-size: 28px; } .kpi .value { font-size: 20px; }
  }
  @media (prefers-reduced-motion: no-preference) { .fill { transition: opacity .15s ease; } }
</style>
"""

BODY = r"""<div class="wrap">
  <header>
    <div class="eyebrow">Fundos exclusivos · BTG e Bradesco</div>
    <h1 id="h1">Receita de gestão</h1>
    <p class="sub" id="sub"></p>
  </header>

  <section class="kpis" aria-label="Indicadores">
    <div class="kpi lead"><div class="label">Receita acumulada no ano</div><div class="value" id="k-ytd"></div><div class="delta" id="k-ytd-d"></div></div>
    <div class="kpi"><div class="label">Média mensal</div><div class="value" id="k-avg"></div><div class="delta" id="k-avg-d"></div></div>
    <div class="kpi"><div class="label" id="k-last-l"></div><div class="value" id="k-last"></div><div class="delta" id="k-last-d"></div></div>
    <div class="kpi"><div class="label">Melhor mês</div><div class="value" id="k-best"></div><div class="delta" id="k-best-d"></div></div>
  </section>

  <div class="grid-2">
    <section class="panel" aria-label="Evolução mensal">
      <h2>Evolução mensal</h2>
      <div class="legend"><span><i class="sw btg"></i>BTG</span><span><i class="sw brad"></i>Bradesco</span><span id="lg-proj" hidden><i class="sw proj"></i>Projeção</span></div>
      <svg class="chart" id="cols" viewBox="0 0 720 300" role="img" aria-label="Receita mensal por instituição"></svg>
      <p class="hint" id="hint-cols"></p>
    </section>
    <section class="panel" aria-label="Contribuição por instituição">
      <h2>Contribuição por instituição</h2>
      <div class="split" id="split"></div>
    </section>
  </div>

  <section class="panel" aria-label="Contribuição por fundo">
    <h2>Contribuição por fundo no ano</h2>
    <p class="hint">Ordenado pela receita acumulada. A cor indica a instituição; as etiquetas marcam início de recebimento e virada de taxa.</p>
    <div class="funds" id="funds"></div>
  </section>

  <section class="panel" aria-label="Observações">
    <h2>Observações</h2>
    <ul class="obs" id="obs"></ul>
  </section>

  <section class="panel" aria-label="Tabela mensal">
    <h2>Receita por fundo e mês</h2>
    <p class="hint">“—” = mês sem recebimento pela BWAG (antes do início) ou sem dados. “(6 d)” = mês parcial, com os dias contabilizados. A linha “Dias contabilizados” mostra a janela cheia de cada mês (último dia útil do mês anterior até o penúltimo do mês).</p>
    <div class="tablewrap"><table id="tbl"></table></div>
  </section>

  <footer>
    <div id="foot"></div>
    <div>Valores = receita líquida de gestão calculada pelo Conferidor de Receita a partir do Informe Diário da CVM (coluna “BWAG · CVM”), não o valor pago pela instituição.</div>
  </footer>
</div>
<div class="tip" id="tip" hidden></div>

<script>
const D = __DATA__;
const $ = s => document.querySelector(s);
const nf = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const brl = v => 'R$ ' + nf.format(v);
const compact = v => v >= 1e6 ? 'R$ ' + (v/1e6).toLocaleString('pt-BR',{maximumFractionDigits:2}) + ' mi'
                 : 'R$ ' + (v/1e3).toLocaleString('pt-BR',{maximumFractionDigits:1}) + ' mil';
const pct = v => (v*100).toLocaleString('pt-BR',{maximumFractionDigits:1}) + '%';
const colLabel = v => (v/1000).toLocaleString('pt-BR',{minimumFractionDigits:1, maximumFractionDigits:1}) + ' mil';
const pctTaxa = v => (v*100).toLocaleString('pt-BR',{minimumFractionDigits:2, maximumFractionDigits:2}) + '%';
const brData = iso => iso ? iso.split('-').reverse().join('/') : '';
const INST = { BTG: 'BTG', BRADESCO: 'Bradesco' };
const cls = i => i === 'BTG' ? 'btg' : 'brad';
const num = v => v == null ? 0 : v;

// ---- agregados
const n = D.meses.length;
const totM = D.meses.map((_, i) => D.fundos.reduce((s, f) => s + num(f.valores[i]), 0));
const instM = { BTG: [], BRADESCO: [] };
for (let i = 0; i < n; i++) for (const k in instM) instM[k][i] = D.fundos.filter(f => f.inst === k).reduce((s, f) => s + num(f.valores[i]), 0);
const ytd = totM.reduce((a, b) => a + b, 0);
const ytdF = D.fundos.map(f => ({ ...f, ytd: f.valores.reduce((a, b) => a + num(b), 0) })).sort((a, b) => b.ytd - a.ytd);
const ytdI = { BTG: instM.BTG.reduce((a,b)=>a+b,0), BRADESCO: instM.BRADESCO.reduce((a,b)=>a+b,0) };
const iMax = totM.indexOf(Math.max(...totM)), iLast = n - 1;
const mesNome = i => D.labels[i] + '/' + D.ano;
const tagsDe = f => {
  const t = [];
  if (f.inicio) t.push(`desde ${brData(f.inicio).slice(0,5)}`);
  if (f.mudanca) t.push(`${pctTaxa(f.mudanca.taxa_gestao)} desde ${brData(f.mudanca.a_partir_de).slice(0,5)}`);
  return t.map(x => `<span class="tag">${x}</span>`).join('');
};

// ---- cabeçalho e KPIs
$('#h1').textContent = `Receita de gestão em ${D.ano}`;
$('#sub').textContent = `Receita líquida de gestão dos ${D.fundos.length} fundos exclusivos, de ${D.labels[0]} a ${D.labels[iLast]} de ${D.ano}, recalculada a partir do PL diário da CVM.`;
$('#k-ytd').textContent = compact(ytd);
$('#k-ytd-d').textContent = brl(ytd) + ' · ' + n + (n === 1 ? ' mês' : ' meses');
$('#k-avg').textContent = compact(ytd / n);
$('#k-avg-d').textContent = brl(ytd / n) + ' por mês';
$('#k-last-l').textContent = mesNome(iLast);
$('#k-last').textContent = compact(totM[iLast]);
{ const el = $('#k-last-d');
  if (n > 1) { const dv = totM[iLast] / totM[iLast-1] - 1;
    el.className = 'delta ' + (dv < 0 ? 'neg' : 'pos');
    el.innerHTML = `<span class="arrow">${dv < 0 ? '▼' : '▲'}</span><span>${pct(Math.abs(dv))} vs ${mesNome(iLast-1)}</span>`; }
  else el.textContent = brl(totM[iLast]); }
$('#k-best').textContent = mesNome(iMax);
$('#k-best-d').textContent = brl(totM[iMax]);

// ---- tooltip
const tip = $('#tip');
function showTip(html, x, y) { tip.innerHTML = html; tip.hidden = false; moveTip(x, y); }
function moveTip(x, y) { const w = tip.offsetWidth, h = tip.offsetHeight;
  tip.style.left = Math.min(x + 14, innerWidth - w - 8) + 'px'; tip.style.top = Math.max(8, Math.min(y - h - 12, innerHeight - h - 8)) + 'px'; }
function hideTip() { tip.hidden = true; }
function bind(el, html) {
  el.addEventListener('mouseenter', e => showTip(html(), e.clientX, e.clientY));
  el.addEventListener('mousemove', e => moveTip(e.clientX, e.clientY));
  el.addEventListener('mouseleave', hideTip);
  el.addEventListener('focus', () => { const r = el.getBoundingClientRect(); showTip(html(), r.left + r.width/2, r.top); });
  el.addEventListener('blur', hideTip);
}

// ---- colunas empilhadas: realizado + projeção (SVG)
{
  const svg = $('#cols'), NS = 'http://www.w3.org/2000/svg';
  const P = D.projecao, nP = P ? P.labels.length : 0, nT = n + nP;
  if (P) $('#lg-proj').hidden = false;
  const W = 720, H = 300, L = 60, R = 12, T = 26, B = 40, pw = W - L - R, ph = H - T - B;
  const maxV = Math.max(...totM, ...(P ? P.total : []), 1);
  const step = maxV > 600000 ? 250000 : 200000, top = Math.ceil(maxV / step) * step;
  const y = v => T + ph - v / top * ph, base = T + ph;
  const el = (t, a) => { const e = document.createElementNS(NS, t); for (const k in a) e.setAttribute(k, a[k]); return e; };
  for (let v = 0; v <= top; v += step) {
    svg.appendChild(el('line', { x1: L, x2: L + pw, y1: y(v), y2: y(v), class: v === 0 ? 'axis' : 'grid' }));
    const t = el('text', { x: L - 8, y: y(v) + 4, 'text-anchor': 'end' }); t.textContent = v === 0 ? '0' : (v/1000) + ' mil'; svg.appendChild(t);
  }
  const band = pw / nT, cw = Math.min(24, band * .45);
  const topRounded = (x, yy, w, h, r) => h <= 0 ? '' :
    `M${x},${yy+h} V${yy+r} Q${x},${yy} ${x+r},${yy} H${x+w-r} Q${x+w},${yy} ${x+w},${yy+r} V${yy+h} Z`;

  // separador entre realizado e projeção
  if (nP) {
    const xs = L + band * n;
    svg.appendChild(el('line', { x1: xs, x2: xs, y1: T - 6, y2: base, class: 'sep' }));
    const st = el('text', { x: xs + 5, y: T - 10, class: 'septxt' }); st.textContent = 'projeção'; svg.appendChild(st);
  }

  const coluna = (k, vB, vR, vT, rotulo, dias, proj, tip, aria) => {
    const cx = L + band * k + band / 2, x0 = cx - cw / 2;
    const hB = vB / top * ph, hR = vR / top * ph;
    const g = el('g', { class: proj ? 'col proj' : 'col' });
    g.appendChild(el('rect', { x: x0, y: base - hB, width: cw, height: hB, fill: 'var(--s-btg)' }));
    g.appendChild(el('path', { d: topRounded(x0, base - hB - (hR > 0 ? 2 : 0) - hR, cw, hR, 4), fill: 'var(--s-brad)' }));
    svg.appendChild(g);
    const destaque = !proj && (k === iMax || k === iLast);
    const t = el('text', { x: cx, y: base - hB - hR - 8, 'text-anchor': 'middle', class: destaque ? 'lbl hi' : 'lbl' });
    t.textContent = colLabel(vT); if (proj) t.setAttribute('opacity', '.75'); svg.appendChild(t);
    const m = el('text', { x: cx, y: H - 17, 'text-anchor': 'middle' }); m.textContent = rotulo; svg.appendChild(m);
    const dd = el('text', { x: cx, y: H - 5, 'text-anchor': 'middle', class: 'dd' }); dd.textContent = dias + 'd'; svg.appendChild(dd);
    const hit = el('rect', { x: L + band * k, y: T, width: band, height: ph, class: 'hit', tabindex: 0, role: 'img', 'aria-label': aria });
    bind(hit, tip); svg.appendChild(hit);
  };

  for (let i = 0; i < n; i++) {
    const d = D.dias_mes ? D.dias_mes[i] : '—';
    coluna(i, instM.BTG[i], instM.BRADESCO[i], totM[i], D.labels[i], d, false,
      () => `<b>${mesNome(i)}</b><div class="r"><span>BTG</span><span>${brl(instM.BTG[i])}</span></div><div class="r"><span>Bradesco</span><span>${brl(instM.BRADESCO[i])}</span></div><div class="r"><span>Dias contabilizados</span><span>${d}</span></div><div class="r"><span><b>Total</b></span><span><b>${brl(totM[i])}</b></span></div>`,
      `${mesNome(i)}: total ${brl(totM[i])}, BTG ${brl(instM.BTG[i])}, Bradesco ${brl(instM.BRADESCO[i])}, ${d} dias`);
  }
  for (let j = 0; j < nP; j++) {
    const nome = P.labels[j] + '/' + D.ano, d = P.dias[j];
    coluna(n + j, P.btg[j], P.brad[j], P.total[j], P.labels[j], d, true,
      () => `<b>${nome}</b> · projeção<div class="r"><span>BTG</span><span>${brl(P.btg[j])}</span></div><div class="r"><span>Bradesco</span><span>${brl(P.brad[j])}</span></div><div class="r"><span>Dias úteis</span><span>${d}</span></div><div class="r"><span><b>Total estimado</b></span><span><b>${brl(P.total[j])}</b></span></div>`,
      `${nome}, projeção: total estimado ${brl(P.total[j])}, ${d} dias úteis`);
  }
}

// ---- divisão por instituição
{
  const s = $('#split'); const pB = ytdI.BTG / ytd, pR = ytdI.BRADESCO / ytd;
  const comInicio = D.fundos.filter(f => f.inicio);
  const nota = comInicio.length
    ? `${comInicio.map(f => f.nome).join(' e ')} entram no acumulado só a partir de ${brData(comInicio[0].inicio)} (ver observações).`
    : '';
  s.innerHTML = `<div class="bar" role="img" aria-label="BTG ${pct(pB)}, Bradesco ${pct(pR)}"><div class="seg btg" style="width:${pB*100}%"></div><div class="seg brad" style="width:${pR*100}%"></div></div>
  <div class="rows">
    <div class="row"><i class="sw btg"></i><span>BTG · ${D.fundos.filter(f=>f.inst==='BTG').length} fundos</span><span class="v">${brl(ytdI.BTG)}</span><span class="p">${pct(pB)}</span></div>
    <div class="row"><i class="sw brad"></i><span>Bradesco · ${D.fundos.filter(f=>f.inst==='BRADESCO').length} fundos</span><span class="v">${brl(ytdI.BRADESCO)}</span><span class="p">${pct(pR)}</span></div>
  </div>
  <div class="note">${nota}</div>`;
}

// ---- barras por fundo
{
  const box = $('#funds'), max = ytdF[0].ytd;
  for (const f of ytdF) {
    const row = document.createElement('div'); row.className = 'fund'; row.tabIndex = 0;
    const mesesCom = f.valores.filter(v => v != null).length;
    row.setAttribute('aria-label', `${f.nome}: ${brl(f.ytd)}, ${pct(f.ytd/ytd)} do total`);
    row.innerHTML = `<div class="n"><i class="dot ${cls(f.inst)}"></i><span class="t">${f.nome}</span>${tagsDe(f)}</div>
      <div class="track"><div class="fill ${cls(f.inst)}" style="width:${f.ytd/max*100}%"></div></div>
      <div class="v">${brl(f.ytd)}</div><div class="p">${pct(f.ytd/ytd)}</div>`;
    bind(row, () => `<b>${f.nome}</b> · ${INST[f.inst]}<div class="r"><span>Acumulado</span><span>${brl(f.ytd)}</span></div><div class="r"><span>Média mensal (${mesesCom} ${mesesCom===1?'mês':'meses'})</span><span>${brl(f.ytd/Math.max(1,mesesCom))}</span></div><div class="r"><span>Último mês</span><span>${f.valores[iLast]==null?'—':brl(f.valores[iLast])}</span></div><div class="r"><span>Dias contabilizados no ano</span><span>${(f.dias||[]).reduce((a,b)=>a+b,0)}</span></div><div class="r"><span>Participação</span><span>${pct(f.ytd/ytd)}</span></div>`);
    box.appendChild(row);
  }
}

// ---- observações (lidas da configuração)
{
  const ul = $('#obs'); const itens = [];
  const porInicio = {};
  for (const f of D.fundos) if (f.inicio) (porInicio[f.inicio] = porInicio[f.inicio] || []).push(f.nome);
  for (const [dt, nomes] of Object.entries(porInicio)) {
    const mes = D.labels[D.meses.indexOf(dt.slice(0,7))] || dt.slice(5,7);
    itens.push(`<li><b>${nomes.join(' e ')}</b>: a BWAG passou a receber a partir de <b>${brData(dt)}</b>. Os meses anteriores aparecem como “—” e ${mes} é parcial (só os dias a partir dessa data).</li>`);
  }
  for (const f of D.fundos) if (f.mudanca) {
    itens.push(`<li><b>${f.nome}</b>: taxa de gestão de ${pctTaxa(f.taxa)} para <b>${pctTaxa(f.mudanca.taxa_gestao)}</b> a partir do PL de <b>${brData(f.mudanca.a_partir_de)}</b> (taxa segregada${f.mudanca.encerra_controladoria ? ', sem desconto de controladoria a partir daí' : ''}). No mês da virada, a controladoria entra proporcional aos dias do regime antigo.</li>`);
  }
  if (D.erros && D.erros.length) itens.push(`<li>Não foi possível calcular a partir de <b>${D.erros[0].mes}</b> (dados da CVM indisponíveis no momento).</li>`);
  if (!itens.length) itens.push('<li>Sem observações para o período.</li>');
  ul.innerHTML = itens.join('');
}

// ---- tabela
{
  const t = $('#tbl');
  const cell = (f, i) => { const v = f.valores[i]; if (v == null) return '<td class="na">—</td>';
    const parcial = D.dias_mes && f.dias && f.dias[i] < D.dias_mes[i] ? `<span class="pd">(${f.dias[i]} d)</span>` : '';
    return `<td>${nf.format(v)}${parcial}</td>`; };
  const diasRow = D.dias_mes ? `<tr class="dias"><td>Dias contabilizados</td><td></td>${D.dias_mes.map(d => `<td>${d}</td>`).join('')}<td>${D.dias_mes.reduce((a,b)=>a+b,0)}</td><td></td></tr>` : '';
  t.innerHTML = `<thead><tr><th>Fundo</th><th>Inst.</th>${D.labels.map(l => `<th>${l}</th>`).join('')}<th>Total ${D.ano}</th><th>%</th></tr></thead>
  <tbody>${ytdF.map(f => `<tr><td>${f.nome}</td><td class="i">${INST[f.inst]}</td>${f.valores.map((_, i) => cell(f, i)).join('')}<td>${nf.format(f.ytd)}</td><td>${pct(f.ytd/ytd)}</td></tr>`).join('')}</tbody>
  <tfoot>${diasRow}<tr><td>Total</td><td></td>${totM.map(v => `<td>${nf.format(v)}</td>`).join('')}<td>${nf.format(ytd)}</td><td>100%</td></tr></tfoot>`;
}

{ const P = D.projecao;
  $('#hint-cols').innerHTML = 'O “21d” embaixo de cada mês é o número de <b>dias contabilizados</b> (último dia útil do mês anterior até o penúltimo do mês).'
    + (P ? ` As colunas claras são <b>projeção</b>: mantêm o PL de ${brData(P.data_pl)} parado e variam só os dias úteis e a taxa vigente de cada fundo — não são previsão de mercado.` : '')
    + ' Passe o mouse ou use Tab para ver a quebra de cada mês.'; }

$('#foot').textContent = `Gerado em ${D.gerado} · Fonte: Portal de Dados Abertos da CVM (Informe Diário de Fundos).`;
</script>
"""
