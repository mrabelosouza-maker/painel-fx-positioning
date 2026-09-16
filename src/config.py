"""Configuracao centralizada: series codes, credenciais, constantes."""
import os

# ──────────────────────────────────────────────────────────────────────
# API Banco Central de Chile
# ──────────────────────────────────────────────────────────────────────
BCENTRAL_CORE = "https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx?"
BCENTRAL_USER = os.environ.get("BCENTRAL_USER", "mrabelo@jgp.com.br")
BCENTRAL_PASS = os.environ.get("BCENTRAL_PASS", "MacroEmergentes@12")
BCENTRAL_FIRSTDATE = "2022-06-01"

# ──────────────────────────────────────────────────────────────────────
# Series FX Positioning (NDF)
# ──────────────────────────────────────────────────────────────────────
SERIES_FX = [
    "F099.DER.STO.Z.40.N.NR.NET.Z.MMUSD.MLME.Z.Z.0.D",   # No residentes
    "F099.DER.STO.Z.40.R.38.NET.Z.MMUSD.MLME.Z.Z.0.D",   # Adm generales de fondos
    "F099.DER.STO.Z.40.R.39.NET.Z.MMUSD.MLME.Z.Z.0.D",   # Corredoras de bolsa
    "F099.DER.STO.Z.40.R.42.NET.Z.MMUSD.MLME.Z.Z.0.D",   # Fondos de pensiones
    "F099.DER.STO.Z.40.R.44.NET.Z.MMUSD.MLME.Z.Z.0.D",   # Companias de seguros
    "F099.DER.STO.Z.40.R.50.NET.Z.MMUSD.MLME.Z.Z.0.D",   # Otros sectores
    "F099.DER.STO.Z.40.R.55A.NET.Z.MMUSD.MLME.Z.Z.0.D",  # Empresas sector real
    "F099.DER.STO.Z.40.R.63.NET.Z.MMUSD.MLME.Z.Z.0.D",   # Residentes no bancos (agregado das seis folhas residentes)
    "F099.DER.STO.Z.40.Z.Z.NET.Z.MMUSD.MLME.Z.Z.0.D",    # Monto vigente neto
]

SERIES_BANCOS = "F099.SPT.STO.Z.40.Z.Z.NET.Z.MMUSD.MLME.Z.Z.0.D"

SERIES_FX_ALL = SERIES_FX + [SERIES_BANCOS]

SERIES_NAMES_ALL = [
    "No residentes",
    "Adm generales de fondos",
    "Corredoras de bolsa",
    "Fondos de pensiones",
    "Companias de seguros",
    "Otros sectores",
    "Empresas sector real",
    "Residentes no bancos",
    "Monto vigente neto",
    "PosicaoBancos",
]

CODIGO_CAMBIO = "F073.TCO.PRE.Z.D"

# ──────────────────────────────────────────────────────────────────────
# Swap Camara series (3 groups x 10 tenors)
# ──────────────────────────────────────────────────────────────────────
SERIES_SWAP_TOTAL = [
    "F099.DER.STO.Z.40.Z.Z.NET.SWP.MMMCLP.SPC.R.HA02.0.D",
    "F099.DER.STO.Z.40.Z.Z.NET.SWP.MMMCLP.SPC.R.MA02.0.D",
    "F099.DER.STO.Z.40.Z.Z.NET.SWP.MMMCLP.SPC.R.ME03.0.D",
    "F099.DER.STO.Z.40.Z.Z.NET.SWP.MMMCLP.SPC.R.ME06.0.D",
    "F099.DER.STO.Z.40.Z.Z.NET.SWP.MMMCLP.SPC.R.ME09.0.D",
    "F099.DER.STO.Z.40.Z.Z.NET.SWP.MMMCLP.SPC.R.ME12.0.D",
    "F099.DER.STO.Z.40.Z.Z.NET.SWP.MMMCLP.SPC.R.ME18.0.D",
    "F099.DER.STO.Z.40.Z.Z.NET.SWP.MMMCLP.SPC.R.AN02.0.D",
    "F099.DER.STO.Z.40.Z.Z.NET.SWP.MMMCLP.SPC.R.AN05.0.D",
    "F099.DER.STO.Z.40.Z.Z.NET.SWP.MMMCLP.SPC.R.MA10.0.D",
]

SERIES_SWAP_OFFSHORE = [
    "F099.DER.STO.Z.40.N.NR.NET.SWP.MMMCLP.SPC.R.HA02.0.D",
    "F099.DER.STO.Z.40.N.NR.NET.SWP.MMMCLP.SPC.R.MA02.0.D",
    "F099.DER.STO.Z.40.N.NR.NET.SWP.MMMCLP.SPC.R.ME03.0.D",
    "F099.DER.STO.Z.40.N.NR.NET.SWP.MMMCLP.SPC.R.ME06.0.D",
    "F099.DER.STO.Z.40.N.NR.NET.SWP.MMMCLP.SPC.R.ME09.0.D",
    "F099.DER.STO.Z.40.N.NR.NET.SWP.MMMCLP.SPC.R.ME12.0.D",
    "F099.DER.STO.Z.40.N.NR.NET.SWP.MMMCLP.SPC.R.ME18.0.D",
    "F099.DER.STO.Z.40.N.NR.NET.SWP.MMMCLP.SPC.R.AN02.0.D",
    "F099.DER.STO.Z.40.N.NR.NET.SWP.MMMCLP.SPC.R.AN05.0.D",
    "F099.DER.STO.Z.40.N.NR.NET.SWP.MMMCLP.SPC.R.MA10.0.D",
]

SERIES_SWAP_LOCAL = [
    "F099.DER.STO.Z.40.R.63.NET.SWP.MMMCLP.SPC.R.HA02.0.D",
    "F099.DER.STO.Z.40.R.63.NET.SWP.MMMCLP.SPC.R.MA02.0.D",
    "F099.DER.STO.Z.40.R.63.NET.SWP.MMMCLP.SPC.R.ME03.0.D",
    "F099.DER.STO.Z.40.R.63.NET.SWP.MMMCLP.SPC.R.ME06.0.D",
    "F099.DER.STO.Z.40.R.63.NET.SWP.MMMCLP.SPC.R.ME09.0.D",
    "F099.DER.STO.Z.40.R.63.NET.SWP.MMMCLP.SPC.R.ME12.0.D",
    "F099.DER.STO.Z.40.R.63.NET.SWP.MMMCLP.SPC.R.ME18.0.D",
    "F099.DER.STO.Z.40.R.63.NET.SWP.MMMCLP.SPC.R.AN02.0.D",
    "F099.DER.STO.Z.40.R.63.NET.SWP.MMMCLP.SPC.R.AN05.0.D",
    "F099.DER.STO.Z.40.R.63.NET.SWP.MMMCLP.SPC.R.MA10.0.D",
]

SWAP_TENOR_NAMES = [
    "ate2y", "apos2y", "3m", "6m", "9m", "12m", "18m", "2y", "5y", "10y",
]

# Durations for DV01 calculation (maps to tenors 3m through 10y)
DURATIONS = [0.24, 0.49, 0.73, 0.95, 1.37, 1.91, 4.43, 9.265]

# Duration mapping: tenor_index -> duration_index
# 3m=idx2->dur0, 6m=idx3->dur1, 9m=idx4->dur2, 12m=idx5->dur3,
# 18m=idx6->dur4, 2y=idx7->dur5, 5y=idx8->dur6, 10y=idx9->dur7
TENOR_DURATION_MAP = {
    "3m": 0.24,
    "6m": 0.49,
    "9m": 0.73,
    "12m": 0.95,
    "18m": 1.37,
    "2y": 1.91,
    "5y": 4.43,
    "10y": 9.265,
}

# ──────────────────────────────────────────────────────────────────────
# Offshore Ajustado
# ──────────────────────────────────────────────────────────────────────
SERIES_SPOT_NR_NETO = "F099.SPT.FLU.Z.40.N.NR.NET.Z.MMUSD.MLME.Z.Z.0.D"
OFFSHORE_ADJ_CUTOVER = "2025-12-15"  # a partir desta data, soma spot acumulado
# 15-dez-2025 = 1o dia util apos o 2o turno, mesma ancora do Santander.
# Trocar a ancora e um deslocamento aditivo puro: muda o nivel, nao a forma nem o z-score.

# Janela em que o grafico de nivel vs USDCLP abre. Nao corta a amostra: o dado
# inteiro vai para o grafico e o zoom (ou duplo-clique) devolve a serie toda.
#
# E o proprio cutover, e nao uma escolha estetica: antes dele a serie e SO a
# perna de NDF, porque o spot acumulado comeca a acumular ali. Abrir antes
# compara duas definicoes diferentes de serie contra o USDCLP, e o resultado e
# um descolamento que nenhuma escala de eixo resolve — a correlacao de nivel vai
# de +0,88 na janela pos-cutover para -0,02 comecando em jan/2025, e a distancia
# media entre as linhas sobe de 8% para 25% da altura do painel.
OFFSHORE_ADJ_DEFAULT_START = OFFSHORE_ADJ_CUTOVER

# Tamanho do bloco do grafico de fluxo por perna, em PREGOES. Semana de
# calendario tem 3, 4 ou 5 pregoes dependendo de feriado, e barras de janelas
# diferentes nao se comparam; 5 pregoes e sempre 5 pregoes.
OFFSHORE_WEEKLY_SESSIONS = 5

# ──────────────────────────────────────────────────────────────────────
# Colombia
# ──────────────────────────────────────────────────────────────────────
COLOMBIA_API_URL = "https://www.datos.gov.co/resource/32sa-8pi3.json"
COLOMBIA_BANREP_URL = (
    "https://suameca.banrep.gov.co/archivos/"
    "sector_externo_tasas_cambio_derivados/mercado_derivados/"
    "series-historico-forward-desde-2016.xlsx"
)
COLOMBIA_LOCAL_FALLBACK = (
    r"R:\Macro EMs\Colombia\7. Externo\series.xlsx"
)

# ──────────────────────────────────────────────────────────────────────
# Oracle DB (Bloomberg data)
# ──────────────────────────────────────────────────────────────────────
ORACLE_UID = "jbamacroreader"
ORACLE_PWD = "Napo1821"
ORACLE_HOST = "jgporaclesrv.jgpdomain.local"
ORACLE_PORT = 1521
ORACLE_CONN_STR = (
    f"oracle+oracledb://{ORACLE_UID}:{ORACLE_PWD}@{ORACLE_HOST}:{ORACLE_PORT}/ORCL"
)

# Bloomberg tickers for FX closing prices
BBG_TICKER_USDCLP = "CLP Curncy"
BBG_TICKER_USDCOP = "COP Curncy"

# ──────────────────────────────────────────────────────────────────────
# Fluxo spot dos fundos de pensao
# ──────────────────────────────────────────────────────────────────────
# Fluxo spot observado do setor 42, otica do banco residente:
# positivo = banco compra USD do AFP = AFP vende USD / compra CLP.
SERIES_SPOT_PENSION = "F099.SPT.FLU.Z.40.R.42.NET.Z.MMUSD.MLME.Z.Z.0.D"

# Serie de NDF do setor 42 (nivel, ja em SERIES_FX): positivo = AFP net short USD.
SERIES_NDF_PENSION_NAME = "Fondos de pensiones"


# ──────────────────────────────────────────────────────────────────────
# Todos os setores: NDF + spot
# ──────────────────────────────────────────────────────────────────────
# O BCCh publica fluxo spot (SPT.FLU) para os mesmos setores do saldo de NDF.
# Chave = nome da coluna de NDF em SERIES_NAMES_ALL, valor = serie de spot.
#
# Cuidado com R.55A e R.63: a descricao do BCCh e um caminho hierarquico, entao
# "Empresas sector real | Residentes no bancos, Monto vigente neto" quer dizer
# que R.55A e a folha e R.63 e o agregado, nao o contrario. Vale nos dois
# namespaces. A verificacao e somar: as seis folhas tem que dar R.63 exato.
SECTOR_SPOT_SERIES = {
    "Fondos de pensiones":     "F099.SPT.FLU.Z.40.R.42.NET.Z.MMUSD.MLME.Z.Z.0.D",
    "Companias de seguros":    "F099.SPT.FLU.Z.40.R.44.NET.Z.MMUSD.MLME.Z.Z.0.D",
    "Empresas sector real":    "F099.SPT.FLU.Z.40.R.55A.NET.Z.MMUSD.MLME.Z.Z.0.D",
    "Corredoras de bolsa":     "F099.SPT.FLU.Z.40.R.39.NET.Z.MMUSD.MLME.Z.Z.0.D",
    "Adm generales de fondos": "F099.SPT.FLU.Z.40.R.38.NET.Z.MMUSD.MLME.Z.Z.0.D",
    "Otros sectores":          "F099.SPT.FLU.Z.40.R.50.NET.Z.MMUSD.MLME.Z.Z.0.D",
    "Residentes no bancos":    "F099.SPT.FLU.Z.40.R.63.NET.Z.MMUSD.MLME.Z.Z.0.D",
    "No residentes":           "F099.SPT.FLU.Z.40.N.NR.NET.Z.MMUSD.MLME.Z.Z.0.D",
    "Monto vigente neto":      "F099.SPT.FLU.Z.40.Z.Z.NET.Z.MMUSD.MLME.Z.Z.0.D",
}

# Hierarquia verificada nos dados (diferenca media de 0,03 MM USD): os seis
# setores residentes somam "Residentes no bancos", e este mais "No residentes"
# soma "Monto vigente neto". Os agregados nao sao setores: entram na tabela como
# linha de soma e ficam fora do grafico, senao contam duas vezes.
SECTOR_LEAVES = [
    "Fondos de pensiones",
    "Companias de seguros",
    "Empresas sector real",
    "Corredoras de bolsa",
    "Adm generales de fondos",
    "Otros sectores",
]
SECTOR_RESIDENT_TOTAL = "Residentes no bancos"
SECTOR_OFFSHORE = "No residentes"
SECTOR_GRAND_TOTAL = "Monto vigente neto"

# Ordem de exibicao da tabela: folhas residentes, o subtotal, o offshore, o total.
SECTOR_TABLE_ORDER = (
    SECTOR_LEAVES + [SECTOR_RESIDENT_TOTAL, SECTOR_OFFSHORE, SECTOR_GRAND_TOTAL]
)
SECTOR_AGGREGATES = {SECTOR_RESIDENT_TOTAL, SECTOR_GRAND_TOTAL}

# As linhas do grafico: as folhas mais o offshore. Sem agregados intermediarios.
SECTOR_CHART_LINES = SECTOR_LEAVES + [SECTOR_OFFSHORE]

# O total do mercado, somado das linhas acima e desenhado destacado.
SECTOR_NET_LINE = "TOTAL (todos os setores)"

# Janelas da aba em PREGOES, nao dias corridos: 1, 5 e 21 sessoes. Dias corridos
# davam janela erratica (7 corridos cobrem 5 pregoes na sexta e 4 na segunda de
# feriado), e o resto do painel ja conta pregao (OFFSHORE_WEEKLY_SESSIONS,
# AFP_DELTA_SESSIONS).
SECTOR_WINDOWS = [1, 5, 21]

# Janelas dos dois empilhados ROLANTES da aba, em pregoes.
SECTOR_ROLLING_SESSIONS = [5, 21]

# Observacoes na janela inicial do eixo x (~6 meses); o zoom-out abre o resto.
SECTOR_ROLLING_DEFAULT_VIEW = 120

# Historico dos rolantes, em pregoes (~1 ano), = 4x a janela inicial.
#
# E orcamento de render, nao preferencia de layout. Plotly em SVG emite um
# retangulo por ponto POR SETOR e desenha todos, inclusive os fora da janela
# inicial do eixo x: sao sete setores, logo 7 retangulos por pregao. Com o
# historico inteiro (~1.550 pregoes) cada grafico passava de dez mil retangulos,
# 82% da aba, e a aba travava — troca de aba e resize disparam relayout, que
# repinta tudo. 250 pregoes dao ~1.750 por grafico.
#
# A composicao por setor de prazo longo se le nos tres empilhados semanais da
# aba, que custam 1/5 por pregao; um rolante de 5 pregoes aberto em seis anos e
# borrao de todo jeito.
SECTOR_ROLLING_HISTORY = 250


# ──────────────────────────────────────────────────────────────────────
# Offshore por prazo: NDF USD-CLP de bancos residentes com no residentes
# ──────────────────────────────────────────────────────────────────────
# Duas familias irmas do mesmo quadro do BDE, uma de estoque e uma de fluxo:
#   STO -> DER_BD_PPC_03, montos VIGENTES netos  (posicao viva)
#   FLU -> DER_BD_SPC_03, montos TRANSADOS netos (novas operacoes do dia)
#
# As duas sao por PLAZO CONTRACTUAL (slot 12 do id = "C"; "R", residual, existe
# em outras tabelas do BDE mas nao nesta). Isso importa: sem prazo residual nao
# ha migracao de balde, entao um contrato fica no balde em que nasceu ate vencer
# e os baldes do estoque e do fluxo sao a MESMA coisa, comparaveis um a um.
#
# O que NAO se segue disso e que o delta do estoque feche a soma do fluxo: o
# fluxo so soma, o vencimento so subtrai e nunca aparece no fluxo. A identidade
# e `delta estoque_i = fluxo_i - vencimentos_i`, e medida na amostra o gap e
# grande (jun/22 a set/26: delta de -17.749 contra fluxo de -66.441 mm USD).
# Por isso a aba mostra as duas coisas, e nao uma como proxy da outra.
OFFSHORE_PRAZO_BALDES = ["P17", "P835", "P3695", "P96185", "P186370", "MA01"]

OFFSHORE_PRAZO_NOMES = {
    "P17":     "Até 7 dias",
    "P835":    "8 a 35 dias",
    "P3695":   "36 a 95 dias",
    "P96185":  "96 a 185 dias",
    "P186370": "186 a 370 dias",
    "MA01":    "Mais de 1 ano",
}


def _serie_prazo(tipo: str, balde: str) -> str:
    """Id de serie do BDE para um balde de prazo. `tipo`: STO (estoque) ou FLU (fluxo)."""
    return f"F099.DER.{tipo}.Z.40.N.NR.NET.NDF.MMUSD.CLPUSD.C.{balde}.0.D"


SERIES_OFFSHORE_PRAZO = {
    "estoque": {b: _serie_prazo("STO", b) for b in OFFSHORE_PRAZO_BALDES},
    "fluxo":   {b: _serie_prazo("FLU", b) for b in OFFSHORE_PRAZO_BALDES},
}

# Agregacao em tres grupos. Os cortes caem onde o mercado ja negocia: ate 35 dias
# pega o roll e o tenor de 1 mes; 36 a 185 pega 2M, 3M e 6M, que e o miolo
# especulativo; 186 para cima pega 9M, 1 ano e o que passa disso.
OFFSHORE_PRAZO_GRUPOS = {
    "Curtíssimo (até 35d)":  ["P17", "P835"],
    "Médio (36 a 185d)":     ["P3695", "P96185"],
    "Longo (186d ou mais)":  ["P186370", "MA01"],
}

# Nome da coluna de total. Tem de comecar com "TOTAL" — e assim que
# make_sector_weekly_stacked separa a linha preta das fatias empilhadas.
OFFSHORE_PRAZO_TOTAL = "TOTAL (todos os prazos)"

# Janelas dos quatro empilhados de fluxo, em pregoes.
OFFSHORE_PRAZO_FLUXO_SESSOES = [5, 21]

# Delta da tabela de estoque, em pregoes.
OFFSHORE_PRAZO_DELTA_SESSOES = 5

# Historico dos seis empilhados, em PREGOES. E orcamento de render e nao recorte
# editorial: Plotly em SVG emite um retangulo por pregao POR BALDE e desenha
# todos, inclusive os fora da janela inicial do eixo x — o `range` recorta a
# vista, nao o DOM. Ver o cabecalho de tests/test_peso_da_pagina.py.
#
# Sao 27 retangulos por pregao na aba (3 figuras de 6 baldes + 3 de 3 grupos),
# entao 190 pregoes custam 5.130. Area sairia de graca, mas nao serve aqui: os
# baldes tem sinal misto e area empilhada do Plotly nao lida bem com isso — foi
# o que desfez o commit 9fb6099 na aba de setores.
#
# 190 pregoes alcancam dez/2025, a mesma ancora de OFFSHORE_ADJ_CUTOVER (o 1o
# dia util apos o 2o turno). Contado em pregao e nao fixado na data de proposito:
# ancora fixa faria o custo crescer ~6.750 retangulos por ano e estourar o teto
# da pagina sozinha, sem ninguem ter feito nada.
OFFSHORE_PRAZO_HISTORICO = 190

# A janela inicial e o historico inteiro: a aba abre ja mostrando dez/2025 ate
# hoje. O zoom-out nao devolve mais do que isso, porque mais do que isso nao
# esta no DOM.
OFFSHORE_PRAZO_DEFAULT_VIEW = OFFSHORE_PRAZO_HISTORICO
