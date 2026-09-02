"""Pipeline principal: calcula a receita de cada fundo para um mês de competência.

Fluxo:
  1. Baixa/lê o Informe Diário da CVM (mês de competência e mês anterior);
  2. Monta a série de PLs do período (último dia útil do mês anterior ->
     penúltimo dia útil do mês de competência);
  3. Aplica a regra de cálculo de cada fundo;
  4. (Opcional) compara com o valor informado pela instituição.
"""

from . import calc, cvm
from .config import carregar_fundos, mudanca_de


def mes_anterior(ano: int, mes: int):
    return (ano - 1, 12) if mes == 1 else (ano, mes - 1)


def calcular_mes(ano: int, mes: int, fundos=None, informado: dict = None):
    """Calcula a receita de todos os fundos para a competência (ano, mes).

    `informado` (opcional): {nome_ou_cnpj_do_fundo: valor_informado_pela_instituicao}.
    Retorna a lista de resultados (um dict por fundo).
    """
    fundos = fundos or carregar_fundos()
    informado = informado or {}

    ym = f"{ano:04d}{mes:02d}"
    aa, mm = mes_anterior(ano, mes)
    ym_ant = f"{aa:04d}{mm:02d}"

    cnpjs = [f.cnpj for f in fundos]
    serie = cvm.ler_series(ym, cnpjs)
    serie_ant = cvm.ler_series(ym_ant, cnpjs)

    resultados = []
    for f in fundos:
        s = cvm.serie_pl(serie, f.cnpj)
        s_ant = cvm.serie_pl(serie_ant, f.cnpj)
        entradas = calc.periodo_pls(s_ant, s)
        pls = [pl for _, pl in entradas]

        # Cota de cada dia (para a memória de cálculo), buscada nos dois meses.
        cotas = {**cvm.serie_cota(serie_ant, f.cnpj), **cvm.serie_cota(serie, f.cnpj)}
        memoria = [
            {
                "data": data,
                "pl": pl,
                "cota": cotas.get(data),
                "ganho_gestao": calc.ganho_gestao_dia(f, pl),
            }
            for data, pl in entradas
        ]

        mudanca = mudanca_de(f.fundo)
        if pls:
            if mudanca:
                componentes = calc.receita_com_mudanca(f, entradas, mudanca)
            else:
                componentes = calc.receita_liquida(f, pls)
        else:
            componentes = {"liquido": None}

        val_informado = informado.get(f.fundo)
        if val_informado is None:
            val_informado = informado.get(f.cnpj)
            if val_informado is None:
                val_informado = informado.get(f.cnpj_num)

        liquido = componentes.get("liquido")
        diferenca = None
        if val_informado is not None and liquido is not None:
            diferenca = round(val_informado - liquido, 2)

        resultados.append(
            {
                "fundo": f.fundo,
                "cnpj": f.cnpj,
                "instituicao": f.instituicao,
                "regra": f.regra,
                "dias": len(pls),
                "data_inicio": entradas[0][0] if entradas else None,
                "data_fim": entradas[-1][0] if entradas else None,
                "componentes": componentes,
                "memoria": memoria,
                "bwag": liquido,
                "informado": val_informado,
                "diferenca": diferenca,
            }
        )
    return resultados


def resumo_texto(resultados) -> str:
    """Formata os resultados como uma tabela de texto simples (para o terminal)."""
    linhas = []
    cab = f"{'FUNDO':30s} {'INST':9s} {'DIAS':>4s} {'BWAG (CVM)':>14s} {'INFORMADO':>14s} {'DIFERENÇA':>12s}"
    linhas.append(cab)
    linhas.append("-" * len(cab))
    tot_bwag = tot_inf = tot_dif = 0.0
    for r in resultados:
        bwag = r["bwag"]
        inf = r["informado"]
        dif = r["diferenca"]
        linhas.append(
            f"{r['fundo'][:30]:30s} {r['instituicao']:9s} {r['dias']:>4d} "
            f"{_fmt(bwag):>14s} {_fmt(inf):>14s} {_fmt(dif):>12s}"
        )
        if isinstance(bwag, (int, float)):
            tot_bwag += bwag
        if isinstance(inf, (int, float)):
            tot_inf += inf
        if isinstance(dif, (int, float)):
            tot_dif += dif
    linhas.append("-" * len(cab))
    linhas.append(
        f"{'TOTAL':30s} {'':9s} {'':>4s} {_fmt(tot_bwag):>14s} {_fmt(tot_inf):>14s} {_fmt(tot_dif):>12s}"
    )
    return "\n".join(linhas)


def _fmt(v):
    if v is None:
        return "-"
    return f"{v:,.2f}"
