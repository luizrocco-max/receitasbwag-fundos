"""Interface de linha de comando do Conferidor de Receita.

Exemplos:
    # calcula junho/2026 e mostra a tabela no terminal
    python -m conferidor --mes 2026-06

    # gera o relatório Excel de conferência
    python -m conferidor --mes 2026-06 --saida relatorios/conferencia_2026-06.xlsx

    # já compara com os valores informados pela instituição (CSV: fundo,valor)
    python -m conferidor --mes 2026-06 --informado informado_jun.csv --saida rel.xlsx
"""

import argparse
import csv
import sys

from . import conferir
from .config import carregar_fundos


def _parse_valor(bruto: str) -> float:
    """Converte texto em número, aceitando formato BR (1.234,56) ou US (1234.56)."""
    bruto = bruto.strip().replace("R$", "").replace(" ", "")
    if "," in bruto:
        # formato brasileiro: ponto é separador de milhar, vírgula é decimal
        bruto = bruto.replace(".", "").replace(",", ".")
    # sem vírgula: assume que o ponto (se houver) já é o separador decimal
    return float(bruto)


def _ler_informado(caminho: str) -> dict:
    """Lê um CSV 'fundo,valor' (ou 'cnpj,valor') com os valores da instituição."""
    valores = {}
    with open(caminho, encoding="utf-8-sig") as f:
        leitor = csv.reader(f)
        for linha in leitor:
            if len(linha) < 2:
                continue
            chave = linha[0].strip()
            try:
                valores[chave] = _parse_valor(linha[1])
            except ValueError:
                continue  # provavelmente o cabeçalho
    return valores


def main(argv=None):
    p = argparse.ArgumentParser(prog="conferidor", description="Conferência de receita dos fundos exclusivos (BWAG) via dados da CVM.")
    p.add_argument("--mes", required=True, help="Mês de competência no formato AAAA-MM (ex.: 2026-06).")
    p.add_argument("--fundos", default=None, help="Caminho do fundos.csv (padrão: o do projeto).")
    p.add_argument("--informado", default=None, help="CSV com os valores informados pela instituição (fundo,valor).")
    p.add_argument("--saida", default=None, help="Caminho do relatório Excel a gerar.")
    args = p.parse_args(argv)

    try:
        ano, mes = (int(x) for x in args.mes.split("-"))
    except ValueError:
        p.error("--mes deve estar no formato AAAA-MM, ex.: 2026-06")

    fundos = carregar_fundos(args.fundos)
    informado = _ler_informado(args.informado) if args.informado else None

    print(f"Baixando/lendo dados da CVM e calculando competência {ano}-{mes:02d} "
          f"({len(fundos)} fundos)...", file=sys.stderr)
    resultados = conferir.calcular_mes(ano, mes, fundos=fundos, informado=informado)

    print(conferir.resumo_texto(resultados))

    if args.saida:
        from . import relatorio
        caminho = relatorio.gerar(resultados, ano, mes, args.saida)
        print(f"\nRelatório salvo em: {caminho}", file=sys.stderr)


if __name__ == "__main__":
    main()
