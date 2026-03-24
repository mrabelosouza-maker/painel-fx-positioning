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
    "F099.DER.STO.Z.40.R.55A.NET.Z.MMUSD.MLME.Z.Z.0.D",  # Residentes no bancos (usado como proxy para Empresas sector real em algumas versoes)
    "F099.DER.STO.Z.40.R.63.NET.Z.MMUSD.MLME.Z.Z.0.D",   # Empresas sector real
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
OFFSHORE_ADJ_CUTOVER = "2025-11-24"  # a partir desta data, soma spot acumulado

# ──────────────────────────────────────────────────────────────────────
# Colombia
# ──────────────────────────────────────────────────────────────────────
COLOMBIA_API_URL = "https://www.datos.gov.co/resource/32sa-8pi3.json"
COLOMBIA_BANREP_URL = (
    "https://www.banrep.gov.co/sites/default/files/"
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
