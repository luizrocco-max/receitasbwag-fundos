"""Testa as viradas de taxa (taxa segregada) do MEMMO e do FINANCE 38 em agosto/2026.

Em ambos, a partir de uma data a gestão passa a uma taxa nova e a controladoria
deixa de ser descontada (o piso do mês entra proporcional aos dias anteriores).

- MEMMO: 0,52% -> 0,42% a partir do PL de 21/08. BTG informou R$ 1.913,42.
- FINANCE 38: 0,43% -> 0,33% a partir do PL de 18/08 (linha 19/08 do BTG). A
  planilha do BTG mostra 0,43% acumulado = 5.239,19 e 0,33% = 3.030,55; o
  robô reproduz ambos e fecha em R$ 6.334,68.

Meses anteriores à virada devem ficar inalterados.
Requer internet (baixa o Informe Diário da CVM de julho e agosto/2026).
"""

from conferidor import calc, conferir, cvm
from conferidor.config import carregar_fundos, mudanca_de


def _res(ano, mes, fundo):
    return {r["fundo"]: r for r in conferir.calcular_mes(ano, mes)}[fundo]


def _split_gestao(fundo_nome, ano, mes):
    """Gestão no regime antigo e no novo, para bater com a planilha do BTG."""
    f = next(x for x in carregar_fundos() if x.fundo == fundo_nome)
    m = mudanca_de(fundo_nome)
    aa, mm = conferir.mes_anterior(ano, mes)
    serie = cvm.ler_series(f"{ano}{mes:02d}", [f.cnpj])
    serie_ant = cvm.ler_series(f"{aa}{mm:02d}", [f.cnpj])
    entradas = calc.periodo_pls(cvm.serie_pl(serie_ant, f.cnpj), cvm.serie_pl(serie, f.cnpj))
    antigo = sum(calc.ganho_composto(f.taxa_gestao, pl) for d, pl in entradas if d < m["a_partir_de"])
    novo = sum(calc.ganho_composto(m["taxa_gestao"], pl) for d, pl in entradas if d >= m["a_partir_de"])
    return antigo, novo


# ---------------- MEMMO ----------------

def test_memmo_agosto_taxa_segregada():
    assert abs(_res(2026, 8, "MEMMO FIM")["bwag"] - 1913.42) <= 0.02


def test_memmo_meses_anteriores_inalterados():
    assert abs(_res(2026, 6, "MEMMO FIM")["bwag"] - 1118.89) <= 0.02
    assert abs(_res(2026, 7, "MEMMO FIM")["bwag"] - 1711.96) <= 0.02


# ---------------- FINANCE 38 ----------------

def test_fin38_agosto_componentes_batem_com_btg():
    antigo, novo = _split_gestao("FIN 38 FAM FIM CP", 2026, 8)
    assert abs(antigo - 5239.19) <= 0.02   # aba ADM do BTG, 0,43% até a linha 18/08
    assert abs(novo - 3030.55) <= 0.02     # aba Gestão do BTG, 0,33% de 19/08 a 31/08


def test_fin38_agosto_liquido():
    r = _res(2026, 8, "FIN 38 FAM FIM CP")
    assert abs(r["componentes"]["controladoria"] - 1935.06) <= 0.02  # piso 3.386,36 x 12/21
    assert abs(r["bwag"] - 6334.68) <= 0.02


def test_fin38_meses_anteriores_inalterados():
    assert abs(_res(2026, 6, "FIN 38 FAM FIM CP")["bwag"] - 5612.63) <= 0.02
    assert abs(_res(2026, 7, "FIN 38 FAM FIM CP")["bwag"] - 6588.61) <= 0.02
