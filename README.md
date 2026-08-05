# Conferidor de Receita — Fundos Exclusivos (BWAG)

Automatiza a conferência da **receita (taxa de gestão)** dos fundos exclusivos.

Hoje esse trabalho é manual: para cada fundo você busca no site da CVM o valor
da cota e o PL, dia a dia, monta a tabela e compara com o que o **BTG** e o
**Bradesco** informam. Esta ferramenta faz a parte trabalhosa sozinha:

1. **Baixa os dados públicos da CVM** (Informe Diário de Fundos), por CNPJ;
2. **Recalcula a receita** de cada fundo pela regra específica dele;
3. **Compara** com o valor informado pela instituição e destaca as diferenças.

A planilha `Conferidor de Receita` original continua sendo a referência — esta
ferramenta foi **validada reproduzindo exatamente os números dela** (ver abaixo).

O relatório em Excel sai com **3 abas**: `Conferência` (resumo com as diferenças
destacadas), `Detalhe` (base de cálculo por fundo) e `Memória de Cálculo`
(**dia a dia**: PL, cota e ganho de cada dia — para bater com a base de cálculo
que o banco envia quando há divergência).

---

## Uso fácil (sem terminal) — para todos

Quem não quiser mexer em terminal usa o **kit de duplo-clique** (ver
`COMO_USAR.txt`):

1. Deixe esta pasta dentro da pasta do **Google Drive** que sincroniza com o PC
   (assim o relatório gerado aparece no Drive para todos verem).
2. **Uma vez:** dê dois cliques em `Instalar_uma_vez.bat` (Windows) ou
   `Instalar_uma_vez.command` (Mac).
3. **Todo mês:** abra `informado.csv`, cole os valores do BTG/Bradesco e salve;
   depois dê dois cliques em `Conferir_Receita.bat` / `.command`, informe o mês
   (`AAAA-MM`) e o relatório abre sozinho.

---

## Como funciona o cálculo

### Período de competência
A receita do mês **M** contempla os PLs do **último dia útil do mês M‑1** até o
**penúltimo dia útil do mês M**. Cada PL gera o "ganho diário" daquele dia.
Ex.: a receita de **junho** vai do último dia útil de **maio** ao penúltimo dia
útil de **junho**. (Os dias úteis são os próprios dias em que a CVM publica o
informe do fundo.)

### Ganho diário
| Instituição | Fórmula do ganho diário |
|---|---|
| **BTG** (composto) | `TRUNC( ((1+taxa)^(1/252)) × PL − PL ; 2 )` |
| **Bradesco** (linear) | `ARRED( (taxa × PL) / 252 ; 2 )` |

> **Bradesco.** A receita da BWAG é a linha **GESTÃO** do relatório do Bradesco.
> A `taxa_gestao` de cada fundo Bradesco já é essa taxa **líquida** (ex.: LUPA
> 0,55%, WASTAFEL 0,50%, KOELKAST 0,75%). O ganho diário é **arredondado** a 2
> casas (como a planilha), não truncado.

O PL usado é o do **dia útil anterior** (convenção de competência da taxa).

### Receita líquida do mês (varia por fundo)
Definida na coluna `regra` do `fundos.csv`:

| Regra | Cálculo |
|---|---|
| `gestao` | soma dos ganhos de gestão (taxa já líquida) |
| `gestao_menos_controladoria` | gestão − MAX(controladoria, piso mínimo) |
| `bradesco_simples` | soma dos ganhos de gestão |
| `bradesco_completo` | gestão − cogestão − extra − controladoria (cada um com piso) |

---

## Fonte dos dados (CVM)

Portal de Dados Abertos da CVM — Informe Diário de Fundos:
`https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/`

Cada arquivo mensal traz, por CNPJ e por dia útil: `VL_QUOTA` (cota),
`VL_PATRIM_LIQ` (PL), entre outros. Os arquivos são baixados sob demanda e ficam
em cache na pasta `dados_cvm/` (não versionada).

> **CNPJ da classe.** Desde a Resolução CVM 175 (2024), o informe identifica os
> fundos pelo **CNPJ da classe** (`CNPJ_FUNDO_CLASSE`). É esse o CNPJ que deve
> estar no `fundos.csv`. A ferramenta também lê o formato antigo (`CNPJ_FUNDO`).

---

## Instalação

```bash
pip install -r requirements.txt   # openpyxl (o acesso à CVM usa só a lib padrão)
```

## Uso

```bash
# calcula a competência e mostra a tabela no terminal
python -m conferidor --mes 2026-06

# gera o relatório de conferência em Excel (layout do painel)
python -m conferidor --mes 2026-06 --saida relatorios/conferencia_2026-06.xlsx

# já compara com os valores informados pela instituição
python -m conferidor --mes 2026-06 \
    --informado exemplos/informado_2026-06.csv \
    --saida relatorios/conferencia_2026-06.xlsx
```

O arquivo `--informado` é um CSV simples com as colunas `fundo` e `valor` — é
onde entram os números que o BTG/Bradesco enviam. A leitura é **robusta para o
Excel brasileiro**: aceita separador `;` (padrão do Excel BR) ou `,`, valores com
vírgula decimal (`43044,85`) ou ponto (`43044.85`), aspas e acentos em qualquer
codificação. O modelo `informado.csv` já vem no formato do Excel BR (`;`).

---

## Configuração dos fundos (`fundos.csv`)

Uma linha por fundo. Colunas principais:

| Coluna | Descrição |
|---|---|
| `fundo` | Nome do fundo (como aparece no painel) |
| `cnpj` | CNPJ da classe (para buscar na CVM) |
| `instituicao` | `BTG` ou `BRADESCO` |
| `regra` | uma das 4 regras da tabela acima |
| `taxa_gestao` | taxa de gestão (fração anual, ex.: `0.0075` = 0,75%) |
| `taxa_controladoria`, `piso_controladoria` | para `gestao_menos_controladoria` |
| `taxa_cogestao`, `taxa_extra`, `taxa_controladoria_brad`, `piso_bradesco` | para `bradesco_completo` |

Para **incluir um novo fundo**, basta adicionar uma linha. Para **mudar uma taxa**,
edite a célula correspondente.

---

## Validação

O motor foi validado contra a planilha original para a competência **junho/2026**
(`python -m pytest tests/ -v`):

- **13 dos 16 fundos** (todos os do BTG): reproduzidos **ao centavo** (diferença R$ 0,00).
- **3 fundos do Bradesco** (LUPA, WASTAFEL, KOELKAST): o recálculo a partir da CVM
  ficou **mais próximo do valor informado pelo Bradesco** do que a própria planilha
  (que tinha pequenas divergências de PL em algum dia).

Além disso, o PL de cada fundo obtido da CVM bate **exatamente** (ao centavo) com
o PL da planilha, aplicando a convenção de "PL do dia útil anterior".

---

## Estrutura do projeto

```
conferidor/
  cvm.py         # download + cache + leitura do Informe Diário da CVM
  calc.py        # fórmulas do ganho diário e da receita líquida por regra
  config.py      # leitura do fundos.csv (registro de fundos)
  conferir.py    # pipeline: monta o período e calcula todos os fundos
  relatorio.py   # gera o Excel de conferência
  __main__.py    # linha de comando (python -m conferidor ...)
fundos.csv       # registro dos fundos e taxas
tests/           # teste de regressão (reproduz junho/2026)
exemplos/        # exemplo de arquivo 'informado'

# Kit de duplo-clique (sem terminal) — ver COMO_USAR.txt
informado.csv            # modelo onde se colam os valores do banco (fundo,valor)
Conferir_Receita.bat     # Windows: roda a conferência do mês
Conferir_Receita.command # Mac: roda a conferência do mês
Instalar_uma_vez.bat     # Windows: instala o necessário (primeira vez)
Instalar_uma_vez.command # Mac: instala o necessário (primeira vez)
```
