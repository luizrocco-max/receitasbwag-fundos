"""Testa a virada de taxa do MEMMO em 21/08/2026 (taxa segregada).

A partir de 21/08 a gestão passou de 0,52% para 0,42% e a controladoria deixou
de ser descontada (o piso do mês entra proporcional aos dias anteriores). O BTG
informou R$ 1.913,42 de receita de gestão para agosto/2026 — este teste garante
que o robô reproduz esse valor, e que meses anteriores ficam inalterados.

Requer internet (baixa o Informe Diário da CVM de julho e agosto/2026).
"""

from conferidor import conferir


def _bwag(ano, mes):
    return {r["fundo"]: r for r in conferir.calcular_mes(ano, mes)}["MEMMO FIM"]["bwag"]


def test_memmo_agosto_taxa_segregada():
    # Valor informado pelo BTG para agosto/2026 (mês da virada).
    assert abs(_bwag(2026, 8) - 1913.42) <= 0.02


def test_memmo_meses_anteriores_inalterados():
    # Antes de 21/08 nada muda: gestão 0,52% menos controladoria (piso cheio).
    assert abs(_bwag(2026, 6) - 1118.89) <= 0.02
    assert abs(_bwag(2026, 7) - 1711.96) <= 0.02
