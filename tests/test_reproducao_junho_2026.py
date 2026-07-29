"""Teste de regressão: reconstruir a receita de junho/2026 a partir da CVM.

Compara o valor recalculado (coluna 'BWAG · CVM' da ferramenta) com o valor que a
planilha original 'Conferidor de Receita' calculou para a mesma competência.

- Fundos BTG: batem ao centavo (diferença esperada 0,00).
- Fundos Bradesco: a ferramenta reproduz o valor recalculado do motor (que, na
  validação, ficou mais próximo do que o Bradesco informou do que a própria
  planilha). Guardamos esses valores como baseline de regressão.

Requer acesso à internet (baixa o Informe Diário da CVM de maio e junho/2026).
Rode com:  python -m pytest tests/ -v
"""

import pytest

from conferidor import conferir

# Valores de referência (R$) para a competência 2026-06.
# BTG -> valores calculados pela planilha original (batem ao centavo).
# Bradesco -> valores do motor recalculado (baseline de regressão).
ESPERADO = {
    "SABIA FIQ FIM CP": 43044.85,
    "EM5 FIM CP": 8417.50,
    "CASULO FIC FIM CP IE": 5529.47,
    "CAVALI HAR FIM CP IE": 17024.15,
    "MAITACA ACOES FC FIA": 100068.50,
    "EXC FR 11 FIM CP IE": 5295.85,
    "SAO MANUEL I P Q FIM": 13954.97,
    "LHC FI MULT": 7234.01,
    "MEMMO FIM": 1118.89,
    "FIN 38 FAM FIM CP": 5612.63,
    "SAMPA 91 FIM CP IE": 32794.16,
    "SAMPA FIF RF INFRA": 6890.47,
    "FALCÃO-PEREGRINO FIM": 4259.89,
    "LUPA FIF CIC MM CP": 102863.69,
    "BRAD WASTAFEL FIF CIC MM CP": 12348.50,
    "BRAD KOELKAST II FIF": 94511.85,
}


@pytest.fixture(scope="module")
def resultados():
    return {r["fundo"]: r for r in conferir.calcular_mes(2026, 6)}


@pytest.mark.parametrize("fundo,esperado", ESPERADO.items())
def test_receita_bwag(resultados, fundo, esperado):
    assert fundo in resultados, f"fundo ausente no resultado: {fundo}"
    obtido = resultados[fundo]["bwag"]
    assert obtido is not None, f"sem cálculo para {fundo}"
    assert abs(obtido - esperado) <= 0.02, f"{fundo}: obtido {obtido:.2f} != esperado {esperado:.2f}"
