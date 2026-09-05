"""Testa o início de recebimento (INICIO_RECEITA) do KOELKAST II e do WASTAFEL.

Os fundos existiam antes, mas a BWAG só passou a receber a partir de 21/05/2026.
Meses anteriores não têm receita (sem cálculo) e maio é parcial: só os dias com
PL >= 21/05. O Bradesco informou maio/2026 = 27.384,18 (KOELKAST) e 3.556,82
(WASTAFEL); o robô reproduz dentro do ruído de arredondamento do Bradesco.

Requer internet (baixa o Informe Diário da CVM de abril a junho/2026).
"""

from conferidor import conferir

KOELKAST = "BRAD KOELKAST II FIF"
WASTAFEL = "BRAD WASTAFEL FIF CIC MM CP"


def _r(ano, mes, fundo):
    return {r["fundo"]: r for r in conferir.calcular_mes(ano, mes)}[fundo]


def test_maio_parcial_bate_com_bradesco():
    k, w = _r(2026, 5, KOELKAST), _r(2026, 5, WASTAFEL)
    assert k["dias"] == 6 and w["dias"] == 6          # 21, 22, 25, 26, 27, 28/05
    assert abs(k["bwag"] - 27384.18) <= 0.10           # ruído de arredondamento do Bradesco
    assert abs(w["bwag"] - 3556.82) <= 0.10


def test_antes_do_inicio_sem_receita():
    for fundo in (KOELKAST, WASTAFEL):
        r = _r(2026, 4, fundo)
        assert r["bwag"] is None and r["dias"] == 0


def test_depois_do_inicio_inalterado():
    # Junho é mês cheio: mesmo baseline de sempre.
    assert abs(_r(2026, 6, KOELKAST)["bwag"] - 94511.97) <= 0.02
    assert abs(_r(2026, 6, WASTAFEL)["bwag"] - 12348.58) <= 0.02
