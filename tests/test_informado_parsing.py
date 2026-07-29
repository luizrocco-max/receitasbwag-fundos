"""Garante que a leitura do informado.csv é robusta ao Excel brasileiro.

O Excel BR usa ';' como separador de colunas e vírgula como decimal, o que
antes embaralhava a leitura. Estes testes travam os formatos aceitos.
"""

from conferidor.__main__ import _ler_informado


def _escrever(tmp_path, nome, conteudo, encoding="utf-8"):
    caminho = tmp_path / nome
    caminho.write_text(conteudo, encoding=encoding)
    return str(caminho)


def test_excel_br_ponto_e_virgula(tmp_path):
    """Formato do Excel BR: separador ';' e vírgula decimal."""
    caminho = _escrever(
        tmp_path,
        "informado.csv",
        "fundo;valor\nSABIA FIQ FIM CP;43044,85\nFALCÃO-PEREGRINO FIM;4259,89\n",
    )
    valores = _ler_informado(caminho)
    assert valores["SABIA FIQ FIM CP"] == 43044.85
    assert valores["FALCÃO-PEREGRINO FIM"] == 4259.89


def test_celula_unica_com_aspas_e_virgula_decimal(tmp_path):
    """Caso 'bagunçado': tudo numa célula, com aspas e vírgula decimal (cp1252)."""
    caminho = _escrever(
        tmp_path,
        "informado.csv",
        'fundo,valor\n"SABIA FIQ FIM CP,43044,85"\n"FALCÃO-PEREGRINO FIM,4259,89"\n',
        encoding="cp1252",
    )
    valores = _ler_informado(caminho)
    assert valores["SABIA FIQ FIM CP"] == 43044.85
    assert valores["FALCÃO-PEREGRINO FIM"] == 4259.89


def test_formato_antigo_virgula_ponto(tmp_path):
    """Compatibilidade: separador ',' com ponto decimal (formato dos exemplos)."""
    caminho = _escrever(
        tmp_path,
        "informado.csv",
        "fundo,valor\nSABIA FIQ FIM CP,43044.85\nEM5 FIM CP,8415.19\n",
    )
    valores = _ler_informado(caminho)
    assert valores["SABIA FIQ FIM CP"] == 43044.85
    assert valores["EM5 FIM CP"] == 8415.19


def test_fundo_sem_valor_e_ignorado(tmp_path):
    """Linha sem valor preenchido não entra no dicionário (não compara)."""
    caminho = _escrever(
        tmp_path, "informado.csv", "fundo;valor\nSABIA FIQ FIM CP;\nEM5 FIM CP;8415,19\n"
    )
    valores = _ler_informado(caminho)
    assert "SABIA FIQ FIM CP" not in valores
    assert valores["EM5 FIM CP"] == 8415.19
