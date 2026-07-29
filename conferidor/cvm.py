"""Acesso ao Informe Diário de Fundos da CVM (Portal de Dados Abertos).

Fonte: https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/
Cada arquivo mensal (inf_diario_fi_AAAAMM.zip) traz, por CNPJ e por dia útil:
  - VL_QUOTA        -> valor da cota
  - VL_PATRIM_LIQ   -> patrimônio líquido (PL)
  - VL_TOTAL, CAPTC_DIA, RESG_DIA, NR_COTST

Os arquivos são baixados sob demanda e ficam em cache local (pasta dados_cvm/),
para não rebaixar o mesmo mês toda vez.
"""

import csv
import io
import os
import ssl
import urllib.request
import zipfile

BASE_URL = "https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/inf_diario_fi_{ym}.zip"

CACHE_DIR = os.environ.get(
    "CVM_CACHE_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dados_cvm"),
)


def _opener():
    """Cria um opener urllib respeitando proxy e CA do ambiente."""
    handlers = []
    proxies = urllib.request.getproxies()
    if proxies:
        handlers.append(urllib.request.ProxyHandler(proxies))
    # ssl.create_default_context() respeita SSL_CERT_FILE/SSL_CERT_DIR do ambiente
    ctx = ssl.create_default_context()
    handlers.append(urllib.request.HTTPSHandler(context=ctx))
    return urllib.request.build_opener(*handlers)


def baixar_mes(ym: str, forcar: bool = False) -> str:
    """Baixa (se necessário) o zip do mês ym='AAAAMM' para o cache. Retorna o caminho."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    destino = os.path.join(CACHE_DIR, f"inf_diario_fi_{ym}.zip")
    if not forcar and os.path.exists(destino) and os.path.getsize(destino) > 0:
        return destino
    url = BASE_URL.format(ym=ym)
    with _opener().open(url, timeout=180) as resp, open(destino, "wb") as out:
        out.write(resp.read())
    return destino


def ler_series(ym: str, cnpjs=None) -> dict:
    """Lê o informe do mês ym='AAAAMM'.

    Retorna {cnpj: {data(str 'AAAA-MM-DD'): {'cota','pl','total','cotistas'}}}.
    Se `cnpjs` for informado, filtra apenas esses CNPJs (mais rápido).
    """
    caminho = baixar_mes(ym)
    alvo = set(cnpjs) if cnpjs else None
    resultado: dict = {}

    with zipfile.ZipFile(caminho) as z:
        nome_csv = z.namelist()[0]
        with z.open(nome_csv) as bruto:
            leitor = csv.DictReader(io.TextIOWrapper(bruto, encoding="latin-1"), delimiter=";")
            # O nome da coluna de CNPJ mudou com a Resolução CVM 175 (2024):
            # CNPJ_FUNDO (formato antigo) -> CNPJ_FUNDO_CLASSE (formato novo).
            campos = leitor.fieldnames or []
            col_cnpj = "CNPJ_FUNDO_CLASSE" if "CNPJ_FUNDO_CLASSE" in campos else "CNPJ_FUNDO"
            for linha in leitor:
                cnpj = linha.get(col_cnpj, "")
                if alvo is not None and cnpj not in alvo:
                    continue
                try:
                    registro = {
                        "cota": float(linha["VL_QUOTA"]),
                        "pl": float(linha["VL_PATRIM_LIQ"]),
                        "total": float(linha["VL_TOTAL"]) if linha.get("VL_TOTAL") else None,
                        "cotistas": int(linha["NR_COTST"]) if linha.get("NR_COTST") else None,
                    }
                except (ValueError, KeyError):
                    continue
                resultado.setdefault(cnpj, {})[linha["DT_COMPTC"]] = registro
    return resultado


def serie_pl(series_mes: dict, cnpj: str) -> dict:
    """Extrai apenas {data: pl} de um resultado de ler_series(), para um CNPJ."""
    return {data: reg["pl"] for data, reg in series_mes.get(cnpj, {}).items()}
