"""Regras de cálculo da receita (taxa de gestão líquida) dos fundos.

Convenções descobertas na planilha original (validadas contra os dados da CVM):

1. COMPETÊNCIA / PERÍODO
   A receita do mês M contempla os PLs do último dia útil do mês M-1 até o
   penúltimo dia útil do mês M. Cada PL gera o "ganho diário" daquele dia.
   (Os dias úteis são os próprios dias em que a CVM publica o informe do fundo.)

2. GANHO DIÁRIO
   - Fundos BTG  -> capitalização composta:
        ganho = TRUNC( ((1+taxa)^(1/252)) * PL - PL , 2 )
   - Fundos Bradesco -> taxa linear (pro-rata 252):
        ganho = ARREDONDA( (taxa * PL) / 252 , 2 )
        (a receita da BWAG é a linha "GESTÃO" do Bradesco; a taxa de gestão de
         cada fundo já é a taxa líquida que a BWAG recebe.)

3. RECEITA LÍQUIDA DO MÊS (varia por fundo - ver `receita_liquida`):
   - gestao                       -> soma dos ganhos de gestão (taxa já líquida)
   - gestao_menos_controladoria   -> gestão - MAX(controladoria, piso)
   - bradesco_simples             -> soma dos ganhos de gestão
   - bradesco_completo            -> gestão - cogestão - extra - controladoria
                                     (cada componente com piso mínimo mensal)
"""

import math


def trunc2(x: float) -> float:
    """Trunca (não arredonda) para 2 casas decimais, como a função TRUNC do Excel."""
    return math.floor(x * 100) / 100 if x >= 0 else math.ceil(x * 100) / 100


def ganho_composto(taxa: float, pl: float) -> float:
    """Ganho diário composto: TRUNC(((1+taxa)^(1/252))*PL - PL, 2)."""
    return trunc2(((1 + taxa) ** (1 / 252)) * pl - pl)


def ganho_linear(taxa: float, pl: float) -> float:
    """Ganho diário linear (pro-rata 252): ARREDONDA (taxa*PL)/252 para 2 casas.

    O Bradesco/planilha arredonda cada dia para 2 casas (não trunca); usar
    arredondamento aproxima melhor o valor informado pela instituição.
    """
    return round((taxa * pl) / 252, 2)


def periodo_pls(serie_mes_anterior: dict, serie_mes: dict):
    """Monta a lista de PLs do período de competência.

    Do último dia útil do mês anterior até o penúltimo dia útil do mês de
    competência (inclusive nos dois extremos).

    serie_* = {data(str 'AAAA-MM-DD'): pl}
    Retorna [(data, pl), ...] em ordem cronológica.
    """
    dias_ant = sorted(serie_mes_anterior)
    dias = sorted(serie_mes)
    entradas = []
    if dias_ant:
        ultimo_mes_ant = dias_ant[-1]
        entradas.append((ultimo_mes_ant, serie_mes_anterior[ultimo_mes_ant]))
    if not dias:
        return entradas
    penultimo = dias[-2] if len(dias) >= 2 else dias[-1]
    for d in dias:
        if d <= penultimo:
            entradas.append((d, serie_mes[d]))
    return entradas


def ganho_gestao_dia(fundo, pl: float) -> float:
    """Ganho de gestão de um único dia, na regra do fundo (composto BTG / linear Bradesco)."""
    if fundo.regra in ("bradesco_simples", "bradesco_completo"):
        return ganho_linear(fundo.taxa_gestao, pl)
    return ganho_composto(fundo.taxa_gestao, pl)


def receita_liquida(fundo, pls) -> dict:
    """Calcula a receita líquida do gestor no mês a partir dos PLs do período.

    `fundo` é um objeto Fundo (ver config.py); `pls` é a lista de PLs (floats).
    Retorna um dicionário com os componentes e a chave 'liquido'.
    """
    regra = fundo.regra

    if regra == "gestao":
        gestao = sum(ganho_composto(fundo.taxa_gestao, pl) for pl in pls)
        return {"gestao": gestao, "liquido": round(gestao, 2)}

    if regra == "gestao_menos_controladoria":
        gestao = sum(ganho_composto(fundo.taxa_gestao, pl) for pl in pls)
        if fundo.taxa_controladoria and fundo.taxa_controladoria > 0:
            ctrl = sum(ganho_composto(fundo.taxa_controladoria, pl) for pl in pls)
            if fundo.piso_controladoria:
                ctrl = max(ctrl, fundo.piso_controladoria)
        else:
            ctrl = 0.0
        return {"gestao": gestao, "controladoria": ctrl, "liquido": round(gestao - ctrl, 2)}

    if regra == "bradesco_simples":
        gestao = sum(ganho_linear(fundo.taxa_gestao, pl) for pl in pls)
        return {"gestao": gestao, "liquido": round(gestao, 2)}

    if regra == "bradesco_completo":
        piso = fundo.piso_bradesco or 0.0
        gestao = sum(ganho_linear(fundo.taxa_gestao, pl) for pl in pls)
        # Componentes acessórios: pro-rata sem truncar, com piso mínimo mensal.
        cogestao = max(sum((pl * (fundo.taxa_cogestao or 0)) / 252 for pl in pls), piso)
        extra = max(sum((pl * (fundo.taxa_extra or 0)) / 252 for pl in pls), piso)
        controladoria = max(sum((pl * (fundo.taxa_controladoria_brad or 0)) / 252 for pl in pls), piso)
        liquido = gestao - cogestao - extra - controladoria
        return {
            "gestao": gestao,
            "cogestao": cogestao,
            "extra": extra,
            "controladoria": controladoria,
            "liquido": round(liquido, 2),
        }

    raise ValueError(f"Regra desconhecida para o fundo {fundo.fundo!r}: {regra!r}")
