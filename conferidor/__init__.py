"""Conferidor de Receita dos Fundos Exclusivos (BWAG).

Automatiza a conferência da receita (taxa de gestão) dos fundos exclusivos:
baixa o Informe Diário da CVM (dados abertos), recalcula a receita de cada
fundo pela regra específica dele e compara com o valor informado pela
instituição (BTG / Bradesco).
"""

from .config import Fundo, carregar_fundos
from . import cvm, calc

__all__ = ["Fundo", "carregar_fundos", "cvm", "calc"]
__version__ = "0.1.0"
