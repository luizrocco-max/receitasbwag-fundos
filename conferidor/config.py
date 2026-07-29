"""Registro dos fundos (config) — carrega o fundos.csv.

Cada linha do fundos.csv descreve um fundo exclusivo e os parâmetros de cálculo
da sua receita. Colunas:

  fundo                    Nome do fundo (como aparece no painel de conferência)
  aba                      Nome da aba original na planilha (referência)
  cnpj                     CNPJ da classe (usado para buscar na CVM)
  instituicao              BTG ou BRADESCO
  regra                    gestao | gestao_menos_controladoria |
                           bradesco_simples | bradesco_completo
  taxa_gestao              Taxa de gestão (fração anual, ex.: 0.0075 = 0,75%)
  taxa_controladoria       (regra gestao_menos_controladoria) taxa de controladoria
  piso_controladoria       (idem) piso mínimo mensal da controladoria em R$
  taxa_cogestao            (regra bradesco_completo) taxa de cogestão
  taxa_extra               (regra bradesco_completo) taxa do componente extra
  taxa_controladoria_brad  (regra bradesco_completo) taxa de controladoria
  piso_bradesco            (regra bradesco_completo) piso mínimo mensal em R$
"""

import csv
import os
from dataclasses import dataclass, field
from typing import Optional

CAMINHO_PADRAO = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fundos.csv"
)


@dataclass
class Fundo:
    fundo: str
    cnpj: str
    instituicao: str
    regra: str
    taxa_gestao: float
    taxa_controladoria: Optional[float] = None
    piso_controladoria: Optional[float] = None
    taxa_cogestao: Optional[float] = None
    taxa_extra: Optional[float] = None
    taxa_controladoria_brad: Optional[float] = None
    piso_bradesco: Optional[float] = None
    aba: str = ""

    @property
    def cnpj_num(self) -> str:
        """CNPJ apenas com dígitos (para comparações tolerantes a formatação)."""
        return "".join(c for c in self.cnpj if c.isdigit())


def _num(valor) -> Optional[float]:
    valor = (valor or "").strip()
    if valor == "":
        return None
    return float(valor.replace(",", "."))


def carregar_fundos(caminho: str = None):
    """Lê o fundos.csv e retorna a lista de objetos Fundo."""
    caminho = caminho or CAMINHO_PADRAO
    fundos = []
    with open(caminho, encoding="utf-8-sig") as f:
        for linha in csv.DictReader(f):
            if not (linha.get("fundo") or "").strip():
                continue
            fundos.append(
                Fundo(
                    fundo=linha["fundo"].strip(),
                    cnpj=linha["cnpj"].strip(),
                    instituicao=linha["instituicao"].strip().upper(),
                    regra=linha["regra"].strip(),
                    taxa_gestao=_num(linha.get("taxa_gestao")),
                    taxa_controladoria=_num(linha.get("taxa_controladoria")),
                    piso_controladoria=_num(linha.get("piso_controladoria")),
                    taxa_cogestao=_num(linha.get("taxa_cogestao")),
                    taxa_extra=_num(linha.get("taxa_extra")),
                    taxa_controladoria_brad=_num(linha.get("taxa_controladoria_brad")),
                    piso_bradesco=_num(linha.get("piso_bradesco")),
                    aba=(linha.get("aba") or "").strip(),
                )
            )
    return fundos
