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


def _ler_texto(caminho: str) -> str:
    """Lê o arquivo tentando as codificações mais comuns (Excel salva em cp1252)."""
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            with open(caminho, encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    with open(caminho, encoding="utf-8", errors="replace") as f:
        return f.read()


def _ler_informado(caminho: str) -> dict:
    """Lê um CSV 'fundo,valor' (ou 'cnpj,valor') com os valores da instituição.

    Robusto para o Excel brasileiro: aceita separador ';' ou ',', valores com
    vírgula decimal (43044,85), aspas e diferentes codificações de acento.
    """
    linhas = _ler_texto(caminho).splitlines()
    # Detecta o separador de colunas: o Excel BR usa ';'; senão, vírgula.
    sep = ";" if any(";" in ln for ln in linhas) else ","

    valores = {}
    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue
        partes = [p.strip().strip('"').strip() for p in linha.split(sep)]
        if len(partes) < 2:
            continue
        chave = partes[0]
        resto = [p for p in partes[1:] if p != ""]
        if not resto:
            continue  # fundo sem valor preenchido -> ignora (não compara)
        # Se o valor veio quebrado em pedaços (vírgula decimal num arquivo
        # separado por vírgula), remonta como decimal brasileiro.
        valor_txt = resto[0] if len(resto) == 1 else f"{resto[0]},{resto[1]}"
        try:
            valores[chave] = _parse_valor(valor_txt)
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
    import urllib.error
    try:
        resultados = conferir.calcular_mes(ano, mes, fundos=fundos, informado=informado)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"\n*** Não foi possível obter os dados da CVM ({e}). ***", file=sys.stderr)
        print("Veja acima como baixar o arquivo manualmente, ou tente novamente mais tarde.",
              file=sys.stderr)
        sys.exit(1)

    print(conferir.resumo_texto(resultados))

    if args.saida:
        from . import relatorio
        try:
            caminho = relatorio.gerar(resultados, ano, mes, args.saida)
            print(f"\nRelatório salvo em: {caminho}", file=sys.stderr)
        except PermissionError:
            print(f"\n*** Não consegui salvar '{args.saida}'. ***", file=sys.stderr)
            print("O arquivo parece estar ABERTO no Excel. Feche-o e rode de novo.",
                  file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
