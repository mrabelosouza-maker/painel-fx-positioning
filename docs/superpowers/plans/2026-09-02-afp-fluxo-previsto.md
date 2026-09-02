# Fluxo AFP previsto a partir de bolsa global — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Medir se o retorno de bolsa global antecipa o fluxo cambial dos fundos de pensão chilenos, entregando um relatório HTML com β̂, estrutura de defasagem e R² fora de amostra.

**Architecture:** Pacote de pesquisa `estudos/afp_leading/`, fora de `src/`, que consome o painel FX Positioning como biblioteca sem modificá-lo. Quatro módulos em cadeia — dados → modelo → avaliação → relatório — cada um com uma responsabilidade e testável isoladamente. Toda a lógica estatística fica em funções puras que recebem DataFrames; só `dados.montar_painel()` toca a rede.

**Tech Stack:** Python 3.11, pandas, numpy, statsmodels (OLS + Newey-West), plotly, pytest 9.

**Spec:** `docs/superpowers/specs/2026-09-02-afp-fluxo-previsto-design.md`

## Global Constraints

- **Nenhuma alteração em `src/`, `templates/`, `tools/` ou `docs/index.html`.** O estudo consome o painel; não o modifica. Qualquer necessidade de mudar `src/` é motivo para parar e perguntar.
- **Amostra fixa:** 2022-06-01 a hoje, ~1.054 observações. É o limite do dado do BCCh; não existe histórico anterior.
- **Convenção de sinal:** todo fluxo está em compra-de-USD (acima de zero = compra de USD), como sai de `data_processor.build_afp_spot_flow`.
- **Unidade de fluxo:** USD milhões. Retornos são logarítmicos e **fracionários** (0,01 = 1%), nunca percentuais. `β = -h·A` só vale com essa combinação.
- **`k = 0` é sempre marcado como não utilizável.** O MXWO fecha depois do mercado cambial chileno; o retorno do mesmo dia não estaria disponível a tempo.
- **Nenhum teste pode tocar a rede.** Testes usam DataFrames sintéticos construídos no próprio teste.
- **Comentários e docstrings em português sem acentuação**, como o resto do repositório (`src/*.py`).

---

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `estudos/afp_leading/__init__.py` | Marca o pacote. Vazio. |
| `estudos/afp_leading/dados.py` | Busca e alinha: fluxo AFP + índices de bolsa num painel diário. Única porta de rede. |
| `estudos/afp_leading/modelo.py` | `Spec`, varredura da estrutura de defasagem, β em janela móvel, portão de sanidade. |
| `estudos/afp_leading/avaliacao.py` | Previsão fora de amostra, R² OOS, split de amostra, teste de plateau. |
| `estudos/afp_leading/relatorio.py` | HTML padrão JGP com os resultados. |
| `estudos/afp_leading/rodar.py` | Entrypoint: encadeia tudo e escreve o relatório. |
| `tests/afp_leading/test_dados.py` | Alinhamento de calendário (função pura). |
| `tests/afp_leading/test_modelo.py` | Recuperação de β conhecido, portão de sanidade. |
| `tests/afp_leading/test_avaliacao.py` | R² OOS, ausência de look-ahead, plateau. |
| `pytest.ini` | Configuração do pytest para o repositório. |

---

### Task 1: Painel de dados alinhado

**Files:**
- Create: `estudos/afp_leading/__init__.py`
- Create: `estudos/afp_leading/dados.py`
- Create: `tests/afp_leading/test_dados.py`
- Create: `pytest.ini`

**Interfaces:**
- Consumes: `src/data_processor.build_fx_dados()`, `src/data_processor.build_afp_spot_flow(dados)`, `src/data_fetcher.fetch_bbg_closing(ticker, col_name, start)`
- Produces:
  - `INDICES: dict[str, str]` — mapeia nome de coluna de retorno para ticker Bloomberg
  - `alinhar(afp: pd.DataFrame, precos: pd.DataFrame) -> pd.DataFrame` — função pura
  - `montar_painel(inicio: str = "2022-06-01") -> pd.DataFrame` — toca a rede
  - Colunas do painel: `Data`, `ndf_1d`, `spot_bcch`, `net_1d`, `r_mxwo`, `r_mxwd`, `r_spx`, `r_mxef`

**A decisão de alinhamento que esta task trava:** os índices e o mercado chileno têm calendários diferentes. O retorno que interessa para o dia útil chileno `t` é o **acumulado do índice desde o dia útil chileno anterior**. Implementação: reindexar o preço do índice nas datas do painel com `ffill` (último fechamento disponível) e só então tirar o log-retorno. Assim um feriado nos EUA vira retorno zero naquele dia e o movimento aparece inteiro no dia seguinte, sem perder nada. O `ffill` aqui é **no nível de preço**, para casar calendário — nunca no fluxo, que é o que a spec proíbe.

- [ ] **Step 1: Criar `pytest.ini` e o pacote de testes**

`pytest.ini` na raiz do repositório:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -q
```

Criar os diretórios e arquivos vazios:

```bash
mkdir -p estudos/afp_leading tests/afp_leading
touch estudos/afp_leading/__init__.py tests/afp_leading/__init__.py
```

- [ ] **Step 2: Escrever o teste que falha**

`tests/afp_leading/test_dados.py`:

```python
"""Alinhamento de calendario entre o fluxo AFP e os indices de bolsa."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from estudos.afp_leading.dados import alinhar


def _afp(datas, net=None):
    n = len(datas)
    return pd.DataFrame({
        "Data": pd.to_datetime(datas),
        "ndf_1d": np.arange(n, dtype=float),
        "spot_bcch": np.zeros(n),
        "net_1d": np.arange(n, dtype=float) if net is None else net,
    })


def test_retorno_acumula_sobre_dia_sem_indice():
    """Feriado no indice: retorno zero no dia, movimento inteiro no seguinte.

    O painel tem 3 dias uteis chilenos; o indice nao negociou no dia 2. O
    retorno do dia 2 tem que ser zero e o do dia 3 tem que carregar o caminho
    inteiro de 100 para 110, nao so o ultimo trecho.
    """
    afp = _afp(["2024-01-02", "2024-01-03", "2024-01-04"])
    precos = pd.DataFrame({
        "Data": pd.to_datetime(["2024-01-02", "2024-01-04"]),
        "MXWO": [100.0, 110.0],
    })

    out = alinhar(afp, precos)

    assert list(out.columns) == ["Data", "ndf_1d", "spot_bcch", "net_1d", "r_MXWO"]
    # primeira linha nao tem retorno definido e sai do painel
    assert len(out) == 2
    assert out["Data"].tolist() == pd.to_datetime(["2024-01-03", "2024-01-04"]).tolist()
    assert out["r_MXWO"].iloc[0] == pytest.approx(0.0)
    assert out["r_MXWO"].iloc[1] == pytest.approx(np.log(110 / 100))


def test_dia_do_afp_sem_preco_anterior_sai_do_painel():
    """Sem fechamento anterior ao inicio, nao ha retorno: a linha nao entra."""
    afp = _afp(["2024-01-02", "2024-01-03"])
    precos = pd.DataFrame({
        "Data": pd.to_datetime(["2024-01-03"]),
        "MXWO": [100.0],
    })

    out = alinhar(afp, precos)

    assert out.empty


def test_dia_do_indice_sem_afp_nao_vira_linha():
    """O painel segue o calendario do AFP; dia extra do indice e ignorado."""
    afp = _afp(["2024-01-02", "2024-01-04"])
    precos = pd.DataFrame({
        "Data": pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
        "MXWO": [100.0, 105.0, 110.0],
    })

    out = alinhar(afp, precos)

    assert out["Data"].tolist() == pd.to_datetime(["2024-01-04"]).tolist()
    # acumula 100 -> 110, passando por 105 sem criar linha
    assert out["r_MXWO"].iloc[0] == pytest.approx(np.log(110 / 100))


def test_fluxo_nao_e_preenchido():
    """NaN no fluxo derruba a linha; nunca vira zero nem ffill."""
    afp = _afp(["2024-01-02", "2024-01-03", "2024-01-04"])
    afp.loc[1, "net_1d"] = np.nan
    precos = pd.DataFrame({
        "Data": pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
        "MXWO": [100.0, 105.0, 110.0],
    })

    out = alinhar(afp, precos)

    assert out["Data"].tolist() == pd.to_datetime(["2024-01-04"]).tolist()
```

- [ ] **Step 3: Rodar o teste e confirmar que falha**

Run: `python -m pytest tests/afp_leading/test_dados.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'estudos.afp_leading.dados'`

- [ ] **Step 4: Implementar `dados.py`**

`estudos/afp_leading/dados.py`:

```python
"""Painel diario do estudo: fluxo AFP + indices de bolsa global.

Unico modulo do estudo que toca a rede. Os demais recebem DataFrames prontos,
para poderem ser testados sem Bloomberg nem BCCh.
"""
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

logger = logging.getLogger(__name__)

# Nome da coluna de retorno -> ticker Bloomberg no Oracle (ODS.MACRO_BBG).
INDICES = {
    "MXWO": "MXWO Index",   # MSCI World, preditor principal
    "MXWD": "MXWD Index",   # MSCI ACWI, cobertura mais ampla
    "SPX": "SPX Index",     # S&P 500, proxy mais liquida
    "MXEF": "MXEF Index",   # MSCI EM, a carteira externa do AFP nao e so DM
}

COLS_FLUXO = ["ndf_1d", "spot_bcch", "net_1d"]
INICIO_PADRAO = "2022-06-01"


def alinhar(afp: pd.DataFrame, precos: pd.DataFrame) -> pd.DataFrame:
    """Casa o fluxo AFP com os indices, no calendario do AFP.

    O retorno de um dia util chileno t e o acumulado do indice desde o dia util
    chileno anterior. Para isso o preco e reindexado nas datas do painel com
    ffill (ultimo fechamento conhecido) e so entao vira log-retorno: um feriado
    la fora sai como retorno zero e o movimento inteiro aparece no dia seguinte,
    sem sumir do acumulado.

    O ffill e no NIVEL DE PRECO, para casar calendario. O fluxo nunca e
    preenchido: dia sem fluxo publicado e linha fora do painel.
    """
    afp = afp.sort_values("Data").reset_index(drop=True)
    precos = precos.sort_values("Data").reset_index(drop=True)

    out = afp.copy()
    datas = pd.DatetimeIndex(out["Data"])
    cols_indice = [c for c in precos.columns if c != "Data"]

    for col in cols_indice:
        serie = precos.set_index("Data")[col].dropna()
        # ffill so propaga para a frente: data do painel anterior ao primeiro
        # fechamento fica NaN, e a linha cai no dropna abaixo.
        nivel = serie.reindex(serie.index.union(datas)).ffill().reindex(datas)
        out[f"r_{col}"] = np.log(nivel.to_numpy() / np.roll(nivel.to_numpy(), 1))
        out.loc[0, f"r_{col}"] = np.nan  # sem dia anterior no painel

    usadas = COLS_FLUXO + [f"r_{c}" for c in cols_indice]
    usadas = [c for c in usadas if c in out.columns]
    out = out.dropna(subset=usadas).reset_index(drop=True)
    return out[["Data"] + usadas]


def montar_painel(inicio: str = INICIO_PADRAO) -> pd.DataFrame:
    """Busca tudo e devolve o painel diario pronto para o modelo.

    Toca a rede: BCCh (via build_fx_dados) e Oracle/Bloomberg (fetch_bbg_closing).
    """
    from data_processor import build_fx_dados, build_afp_spot_flow
    from data_fetcher import fetch_bbg_closing

    dados = build_fx_dados()
    afp = build_afp_spot_flow(dados)[["Data"] + COLS_FLUXO]
    logger.info("Fluxo AFP: %d linhas (%s a %s)", len(afp),
                afp["Data"].min().date(), afp["Data"].max().date())

    precos = None
    for nome, ticker in INDICES.items():
        df = fetch_bbg_closing(ticker, nome, start=inicio)
        if df.empty:
            raise RuntimeError(f"Indice {ticker} voltou vazio do Oracle")
        precos = df if precos is None else precos.merge(df, on="Data", how="outer")

    painel = alinhar(afp, precos)
    logger.info("Painel: %d linhas (%s a %s)", len(painel),
                painel["Data"].min().date(), painel["Data"].max().date())
    return painel
```

- [ ] **Step 5: Rodar os testes e confirmar que passam**

Run: `python -m pytest tests/afp_leading/test_dados.py -v`
Expected: PASS, 4 testes

- [ ] **Step 6: Verificar `montar_painel` contra o dado real**

Run:

```bash
python -c "
import sys; sys.path.insert(0, '.')
import logging; logging.basicConfig(level=logging.INFO)
from estudos.afp_leading.dados import montar_painel
p = montar_painel()
print(p.shape)
print(p.head(3).to_string())
print(p[['net_1d','r_MXWO']].describe().to_string())
"
```

Expected: entre 900 e 1.100 linhas; `r_MXWO` com desvio-padrão entre 0,005 e 0,020 (bolsa global diária); `net_1d` com média perto de zero e desvio de dezenas a centenas de USD mm. Se `r_MXWO` sair com desvio > 0,05, o retorno foi computado em percentual em vez de fracionário — parar e corrigir.

- [ ] **Step 7: Commit**

```bash
git add pytest.ini estudos/afp_leading tests/afp_leading
git commit -m "estudo AFP: painel diario de fluxo e bolsa global

Alinhamento no calendario do AFP: o retorno de um dia util chileno e o
acumulado do indice desde o dia util chileno anterior. ffill no nivel de preco
para casar calendario, nunca no fluxo."
```

---

### Task 2: Estrutura de defasagem

**Files:**
- Create: `estudos/afp_leading/modelo.py`
- Create: `tests/afp_leading/test_modelo.py`

**Interfaces:**
- Consumes: painel de `dados.alinhar` / `dados.montar_painel` (colunas `Data`, `ndf_1d`, `net_1d`, `r_*`)
- Produces:
  - `Spec = namedtuple("Spec", ["alvo", "preditor", "tipo", "n"])` — `tipo` é `"pontual"` ou `"acumulada"`
  - `serie_preditora(painel: pd.DataFrame, spec: Spec) -> pd.Series`
  - `estrutura_defasagem(painel, alvo, preditor, ks=range(0, 11), ws=range(1, 22)) -> pd.DataFrame`
  - Colunas devolvidas: `tipo`, `n`, `beta`, `se`, `tstat`, `r2`, `utilizavel`, `h_a_bi`

**Contrato das duas famílias de especificação:**

| Tipo | `n` | Preditor em `t` | Utilizável |
|---|---|---|---|
| `pontual` | `k` | `r(t-k)` | `k >= 1` |
| `acumulada` | `w` | `soma de r(t-w) ate r(t-1)` | sempre |

A acumulada usa `shift(1)` antes de somar, então nunca inclui `r(t)`. É utilizável por construção.

`h_a_bi` é a exposição hedgeada implícita em USD **bilhões**: `-beta / 1000`, já que `beta` sai em USD mm por unidade de retorno fracionário.

- [ ] **Step 1: Escrever o teste que falha**

`tests/afp_leading/test_modelo.py`:

```python
"""Recuperacao de beta conhecido e portao de sanidade."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from estudos.afp_leading.modelo import Spec, serie_preditora, estrutura_defasagem


def painel_sintetico(n=800, k_verdadeiro=3, beta_verdadeiro=-30000.0, ruido=40.0, seed=7):
    """Fluxo gerado por beta * retorno defasado de k dias, mais ruido branco.

    beta = -30000 significa que 1% de bolsa move 300 USD mm de hedge, e uma
    exposicao hedgeada implicita de USD 30 bi — dentro da faixa plausivel.
    """
    rng = np.random.default_rng(seed)
    r = rng.normal(0, 0.01, n)
    fluxo = beta_verdadeiro * np.roll(r, k_verdadeiro) + rng.normal(0, ruido, n)
    fluxo[:k_verdadeiro] = np.nan
    return pd.DataFrame({
        "Data": pd.bdate_range("2022-06-01", periods=n),
        "net_1d": fluxo,
        "ndf_1d": fluxo,
        "r_MXWO": r,
    }).dropna().reset_index(drop=True)


def test_serie_preditora_pontual_desloca_k_dias():
    painel = pd.DataFrame({
        "Data": pd.bdate_range("2024-01-01", periods=5),
        "r_MXWO": [0.01, 0.02, 0.03, 0.04, 0.05],
    })
    s = serie_preditora(painel, Spec("net_1d", "r_MXWO", "pontual", 2))
    assert np.isnan(s.iloc[0]) and np.isnan(s.iloc[1])
    assert s.iloc[2] == pytest.approx(0.01)
    assert s.iloc[4] == pytest.approx(0.03)


def test_serie_preditora_acumulada_nunca_inclui_o_dia():
    """Janela w=2 em t soma r(t-2) e r(t-1); r(t) fica de fora."""
    painel = pd.DataFrame({
        "Data": pd.bdate_range("2024-01-01", periods=5),
        "r_MXWO": [0.01, 0.02, 0.03, 0.04, 0.05],
    })
    s = serie_preditora(painel, Spec("net_1d", "r_MXWO", "acumulada", 2))
    assert s.iloc[2] == pytest.approx(0.01 + 0.02)
    assert s.iloc[4] == pytest.approx(0.03 + 0.04)


def test_estrutura_encontra_a_defasagem_verdadeira():
    painel = painel_sintetico(k_verdadeiro=3, beta_verdadeiro=-30000.0)
    tab = estrutura_defasagem(painel, "net_1d", "r_MXWO")

    pontuais = tab[tab["tipo"] == "pontual"]
    vencedor = pontuais.loc[pontuais["r2"].idxmax()]
    assert vencedor["n"] == 3
    assert vencedor["beta"] == pytest.approx(-30000.0, rel=0.15)
    assert vencedor["tstat"] < -5


def test_h_a_implicito_em_bilhoes():
    painel = painel_sintetico(k_verdadeiro=3, beta_verdadeiro=-30000.0)
    tab = estrutura_defasagem(painel, "net_1d", "r_MXWO")
    linha = tab[(tab["tipo"] == "pontual") & (tab["n"] == 3)].iloc[0]
    # beta -30000 USD mm por unidade de retorno -> h*A = USD 30 bi
    assert linha["h_a_bi"] == pytest.approx(30.0, rel=0.15)


def test_k_zero_marcado_nao_utilizavel():
    painel = painel_sintetico()
    tab = estrutura_defasagem(painel, "net_1d", "r_MXWO")
    k0 = tab[(tab["tipo"] == "pontual") & (tab["n"] == 0)].iloc[0]
    assert not k0["utilizavel"]
    assert tab[tab["tipo"] == "acumulada"]["utilizavel"].all()
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `python -m pytest tests/afp_leading/test_modelo.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'estudos.afp_leading.modelo'`

- [ ] **Step 3: Implementar `modelo.py`**

`estudos/afp_leading/modelo.py`:

```python
"""Estrutura de defasagem entre bolsa global e fluxo AFP.

Convencao de unidades, que faz o beta significar alguma coisa: fluxo em USD
milhoes, retorno logaritmico FRACIONARIO (0,01 = 1%). Com isso o modelo
    fluxo = a + beta * r
tem beta = -h*A, onde h e a razao de hedge e A a carteira externa em USD mm.
Bolsa sobe -> carteira externa vale mais -> o AFP vende USD a termo -> fluxo
negativo na convencao de compra-de-USD, logo beta negativo.
"""
from collections import namedtuple

import numpy as np
import pandas as pd
import statsmodels.api as sm

Spec = namedtuple("Spec", ["alvo", "preditor", "tipo", "n"])

KS_PADRAO = range(0, 11)
WS_PADRAO = range(1, 22)


def serie_preditora(painel: pd.DataFrame, spec: Spec) -> pd.Series:
    """O X de uma especificacao, sempre so com informacao anterior a t.

    pontual k   -> r(t-k)
    acumulada w -> soma de r(t-w) ate r(t-1); o shift(1) antes do rolling
                   garante que r(t) nunca entra.
    """
    r = painel[spec.preditor]
    if spec.tipo == "pontual":
        return r.shift(spec.n)
    if spec.tipo == "acumulada":
        return r.shift(1).rolling(spec.n).sum()
    raise ValueError(f"tipo desconhecido: {spec.tipo}")


def _ajustar(painel: pd.DataFrame, spec: Spec):
    """OLS com erro-padrao Newey-West. Devolve (resultado, n_obs) ou (None, 0).

    A defasagem do Newey-West acompanha a janela: nas acumuladas as observacoes
    se sobrepoem e os residuos sao autocorrelacionados por construcao.
    """
    x = serie_preditora(painel, spec)
    y = painel[spec.alvo]
    d = pd.DataFrame({"y": y, "x": x}).dropna()
    if len(d) < 30:
        return None, len(d)
    maxlags = max(1, spec.n if spec.tipo == "acumulada" else 1)
    m = sm.OLS(d["y"], sm.add_constant(d["x"])).fit(
        cov_type="HAC", cov_kwds={"maxlags": maxlags}
    )
    return m, len(d)


def estrutura_defasagem(
    painel: pd.DataFrame,
    alvo: str,
    preditor: str,
    ks=KS_PADRAO,
    ws=WS_PADRAO,
) -> pd.DataFrame:
    """Varre as duas familias de especificacao. Uma linha por especificacao.

    k = 0 entra na tabela mas sai marcado como nao utilizavel: o MXWO fecha
    depois do mercado cambial chileno, entao o retorno do mesmo dia nao estaria
    disponivel a tempo. Serve so como referencia de quanto do fluxo e
    contemporaneo.
    """
    linhas = []
    grade = [("pontual", k) for k in ks] + [("acumulada", w) for w in ws]

    for tipo, n in grade:
        spec = Spec(alvo, preditor, tipo, n)
        m, nobs = _ajustar(painel, spec)
        if m is None:
            continue
        beta = float(m.params.iloc[1])
        se = float(m.bse.iloc[1])
        linhas.append({
            "tipo": tipo,
            "n": n,
            "beta": beta,
            "se": se,
            "tstat": float(m.tvalues.iloc[1]),
            "r2": float(m.rsquared),
            "nobs": nobs,
            "utilizavel": tipo == "acumulada" or n >= 1,
            "h_a_bi": -beta / 1000.0,
        })

    return pd.DataFrame(linhas)
```

- [ ] **Step 4: Rodar os testes e confirmar que passam**

Run: `python -m pytest tests/afp_leading/test_modelo.py -v`
Expected: PASS, 5 testes

- [ ] **Step 5: Commit**

```bash
git add estudos/afp_leading/modelo.py tests/afp_leading/test_modelo.py
git commit -m "estudo AFP: varredura da estrutura de defasagem

Duas familias de especificacao (pontual k e acumulada w), OLS com Newey-West
cuja defasagem acompanha a janela. k=0 entra na tabela mas sai marcado como nao
utilizavel: o MXWO fecha depois do mercado cambial chileno."
```

---

### Task 3: β em janela móvel e portão de sanidade

**Files:**
- Modify: `estudos/afp_leading/modelo.py` (acrescenta ao fim)
- Modify: `tests/afp_leading/test_modelo.py` (acrescenta ao fim)

**Interfaces:**
- Consumes: `Spec`, `serie_preditora` da Task 2
- Produces:
  - `beta_movel(painel: pd.DataFrame, spec: Spec, janela: int | None = None, min_treino: int = 252) -> pd.DataFrame` — colunas `Data`, `beta`
  - `FAIXA_H_A_BI = (5.0, 90.0)`
  - `portao_sanidade(beta: float, faixa=FAIXA_H_A_BI) -> tuple[bool, str]`

`janela=None` dá janela expansível; `janela=252` dá móvel de 252 dias. Em ambos os casos o β em `Data[i]` usa **apenas** observações até `i-1`, para nunca carregar coeficiente do futuro.

- [ ] **Step 1: Escrever os testes que falham**

Acrescentar ao fim de `tests/afp_leading/test_modelo.py`:

```python
from estudos.afp_leading.modelo import beta_movel, portao_sanidade, FAIXA_H_A_BI


def test_beta_movel_converge_para_o_verdadeiro():
    painel = painel_sintetico(n=900, k_verdadeiro=3, beta_verdadeiro=-30000.0)
    bm = beta_movel(painel, Spec("net_1d", "r_MXWO", "pontual", 3))

    assert list(bm.columns) == ["Data", "beta"]
    assert bm["beta"].notna().sum() > 500
    assert bm["beta"].dropna().iloc[-1] == pytest.approx(-30000.0, rel=0.15)


def test_beta_movel_nao_usa_o_futuro():
    """Trocar o dado depois de uma data nao pode mudar o beta naquela data."""
    painel = painel_sintetico(n=900, k_verdadeiro=3, beta_verdadeiro=-30000.0)
    spec = Spec("net_1d", "r_MXWO", "pontual", 3)
    bm1 = beta_movel(painel, spec)

    corrompido = painel.copy()
    corrompido.loc[600:, "net_1d"] = corrompido.loc[600:, "net_1d"] * -5.0
    bm2 = beta_movel(corrompido, spec)

    corte = 500
    a = bm1.iloc[:corte]["beta"].to_numpy()
    b = bm2.iloc[:corte]["beta"].to_numpy()
    np.testing.assert_allclose(a, b, equal_nan=True)


def test_portao_aceita_magnitude_plausivel():
    ok, msg = portao_sanidade(-30000.0)
    assert ok, msg


def test_portao_rejeita_beta_positivo():
    ok, msg = portao_sanidade(30000.0)
    assert not ok
    assert "positivo" in msg.lower()


def test_portao_rejeita_magnitude_absurda():
    ok, msg = portao_sanidade(-500000.0)  # h*A = USD 500 bi
    assert not ok
    assert "500" in msg
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `python -m pytest tests/afp_leading/test_modelo.py -v`
Expected: FAIL com `ImportError: cannot import name 'beta_movel'`

- [ ] **Step 3: Implementar, acrescentando ao fim de `modelo.py`**

```python
# Faixa de exposicao hedgeada implicita (h*A) aceitavel, em USD bilhoes.
# Checagem de ordem de grandeza, nao de precisao: a carteira externa do AFP e da
# ordem de dezenas de bilhoes e a razao de hedge historicamente varia numa faixa
# larga. Se h*A cair perto de qualquer borda, confrontar com o ativo externo
# publicado pela Superintendencia de Pensiones antes de seguir.
FAIXA_H_A_BI = (5.0, 90.0)


def beta_movel(
    painel: pd.DataFrame,
    spec: Spec,
    janela: int | None = None,
    min_treino: int = 252,
) -> pd.DataFrame:
    """Beta estimado so com dado anterior a cada data.

    janela=None  -> expansivel (toda a historia ate t-1)
    janela=252   -> movel de 252 observacoes terminando em t-1

    O beta na linha i NUNCA usa a observacao i nem nenhuma posterior: e esse
    beta que a fase 2 usaria para prever, e um beta contaminado pelo futuro
    inventaria performance.
    """
    x = serie_preditora(painel, spec).to_numpy()
    y = painel[spec.alvo].to_numpy()
    valido = ~(np.isnan(x) | np.isnan(y))

    betas = np.full(len(painel), np.nan)
    for i in range(len(painel)):
        ini = 0 if janela is None else max(0, i - janela)
        sel = valido.copy()
        sel[:ini] = False
        sel[i:] = False  # exclui a propria observacao e todo o futuro
        if sel.sum() < min_treino:
            continue
        xi, yi = x[sel], y[sel]
        m = sm.OLS(yi, sm.add_constant(xi)).fit()
        betas[i] = float(m.params[1])

    return pd.DataFrame({"Data": painel["Data"].to_numpy(), "beta": betas})


def portao_sanidade(beta: float, faixa=FAIXA_H_A_BI) -> tuple[bool, str]:
    """Checa se o beta e compativel com o mecanismo antes de gastar o resto.

    Duas condicoes: sinal negativo (bolsa sobe -> AFP vende USD a termo) e
    exposicao hedgeada implicita de ordem de grandeza plausivel.
    """
    if not np.isfinite(beta):
        return False, "beta nao finito"
    if beta >= 0:
        return False, (
            f"beta positivo ({beta:,.0f}): bolsa subindo com o AFP comprando USD "
            "contraria o mecanismo de hedge. A hipotese esta errada, nao o ajuste."
        )
    h_a = -beta / 1000.0
    lo, hi = faixa
    if not (lo <= h_a <= hi):
        return False, (
            f"exposicao hedgeada implicita de USD {h_a:,.1f} bi fora da faixa "
            f"[{lo:,.0f}, {hi:,.0f}] bi"
        )
    return True, f"beta {beta:,.0f} -> h*A implicito de USD {h_a:,.1f} bi"
```

- [ ] **Step 4: Rodar os testes e confirmar que passam**

Run: `python -m pytest tests/afp_leading/test_modelo.py -v`
Expected: PASS, 10 testes

- [ ] **Step 5: Commit**

```bash
git add estudos/afp_leading/modelo.py tests/afp_leading/test_modelo.py
git commit -m "estudo AFP: beta em janela movel e portao de sanidade

O beta na linha i nunca usa a observacao i nem nenhuma posterior, com teste que
corrompe o futuro e verifica que o passado nao muda. Portao exige beta negativo
e h*A implicito entre USD 5 bi e 90 bi."
```

---

### Task 4: Avaliação fora de amostra e plateau

**Files:**
- Create: `estudos/afp_leading/avaliacao.py`
- Create: `tests/afp_leading/test_avaliacao.py`

**Interfaces:**
- Consumes: `modelo.Spec`, `modelo.serie_preditora`, `modelo.beta_movel`; painel de `dados`
- Produces:
  - `previsao_oos(painel, spec, min_treino=252) -> pd.DataFrame` — colunas `Data`, `realizado`, `previsto`
  - `r2_oos(realizado: np.ndarray, previsto: np.ndarray) -> float`
  - `avaliar(painel, spec, min_treino=252) -> dict` — chaves `r2_oos`, `corr`, `mae_usd_mm`, `nobs`, `metades`
  - `tem_plateau(tabela: pd.DataFrame, tipo: str, n: int, aval_por_spec: dict) -> tuple[bool, str]`

**R² fora de amostra:** `1 - SSE_modelo / SSE_referencia`, com a referência sendo a **média expansível do próprio fluxo** até `t-1` — não zero, não a média da amostra cheia. Positivo significa que o modelo bate o "chute da média histórica". É a definição de Campbell-Thompson, e pode ser negativa.

**Plateau:** a especificação vencedora precisa de vizinhos vivos. Para `(tipo, n)`, olhar `n-1` e `n+1` da mesma família: cada vizinho existente precisa ter `beta` do mesmo sinal e `r2_oos` de pelo menos **metade** do vencedor. Se nenhum vizinho existir na grade, falha.

- [ ] **Step 1: Escrever o teste que falha**

`tests/afp_leading/test_avaliacao.py`:

```python
"""Metricas fora de amostra e teste de plateau."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from estudos.afp_leading.modelo import Spec
from estudos.afp_leading.avaliacao import (
    previsao_oos, r2_oos, avaliar, tem_plateau,
)
from tests.afp_leading.test_modelo import painel_sintetico


def test_r2_oos_zero_quando_modelo_iguala_a_media():
    y = np.array([1.0, 2.0, 3.0, 4.0])
    # previsao identica a media expansivel -> nao ganha nada da referencia
    assert r2_oos(y, np.array([1.0, 1.0, 1.5, 2.0])) == pytest.approx(0.0)


def test_r2_oos_positivo_quando_modelo_acerta_mais():
    y = np.array([1.0, 2.0, 3.0, 4.0])
    assert r2_oos(y, y) == pytest.approx(1.0)


def test_r2_oos_negativo_quando_modelo_erra_mais_que_a_media():
    y = np.array([1.0, 2.0, 3.0, 4.0])
    assert r2_oos(y, np.array([50.0, 50.0, 50.0, 50.0])) < 0


def test_previsao_oos_nao_usa_o_futuro():
    painel = painel_sintetico(n=900, k_verdadeiro=3, beta_verdadeiro=-30000.0)
    spec = Spec("net_1d", "r_MXWO", "pontual", 3)
    p1 = previsao_oos(painel, spec)

    corrompido = painel.copy()
    corrompido.loc[600:, "net_1d"] = corrompido.loc[600:, "net_1d"] * -5.0
    p2 = previsao_oos(corrompido, spec)

    corte = 500
    np.testing.assert_allclose(
        p1.iloc[:corte]["previsto"].to_numpy(),
        p2.iloc[:corte]["previsto"].to_numpy(),
        equal_nan=True,
    )


def test_avaliar_recupera_relacao_forte():
    painel = painel_sintetico(n=900, k_verdadeiro=3, beta_verdadeiro=-30000.0, ruido=40.0)
    a = avaliar(painel, Spec("net_1d", "r_MXWO", "pontual", 3))

    assert a["r2_oos"] > 0.10
    assert a["corr"] > 0.5
    assert a["mae_usd_mm"] > 0
    assert set(a["metades"]) == {"primeira", "segunda"}
    assert a["metades"]["primeira"]["beta"] < 0
    assert a["metades"]["segunda"]["beta"] < 0


def test_avaliar_nao_encontra_relacao_em_ruido_puro():
    painel = painel_sintetico(n=900, beta_verdadeiro=0.0, ruido=40.0)
    a = avaliar(painel, Spec("net_1d", "r_MXWO", "pontual", 3))
    assert a["r2_oos"] < 0.05


def _tabela(betas_r2):
    """betas_r2: lista de (n, beta, r2_oos) para a familia pontual."""
    return pd.DataFrame([
        {"tipo": "pontual", "n": n, "beta": b, "r2_oos": r}
        for n, b, r in betas_r2
    ])


def test_plateau_aceita_vizinhos_vivos():
    tab = _tabela([(2, -25000, 0.12), (3, -30000, 0.20), (4, -22000, 0.11)])
    aval = {(r.tipo, r.n): {"r2_oos": r.r2_oos, "beta": r.beta} for r in tab.itertuples()}
    ok, msg = tem_plateau(tab, "pontual", 3, aval)
    assert ok, msg


def test_plateau_rejeita_pico_isolado():
    tab = _tabela([(2, -1000, 0.01), (3, -30000, 0.20), (4, 500, 0.00)])
    aval = {(r.tipo, r.n): {"r2_oos": r.r2_oos, "beta": r.beta} for r in tab.itertuples()}
    ok, msg = tem_plateau(tab, "pontual", 3, aval)
    assert not ok
    assert "vizinho" in msg.lower()


def test_plateau_rejeita_vizinho_de_sinal_trocado():
    tab = _tabela([(2, 26000, 0.15), (3, -30000, 0.20), (4, -28000, 0.18)])
    aval = {(r.tipo, r.n): {"r2_oos": r.r2_oos, "beta": r.beta} for r in tab.itertuples()}
    ok, msg = tem_plateau(tab, "pontual", 3, aval)
    assert not ok
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `python -m pytest tests/afp_leading/test_avaliacao.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'estudos.afp_leading.avaliacao'`

- [ ] **Step 3: Implementar `avaliacao.py`**

`estudos/afp_leading/avaliacao.py`:

```python
"""Metricas fora de amostra e a defesa contra a busca por especificacao."""
import numpy as np
import pandas as pd
import statsmodels.api as sm

from .modelo import Spec, serie_preditora


def r2_oos(realizado: np.ndarray, previsto: np.ndarray) -> float:
    """R2 fora de amostra a la Campbell-Thompson.

    1 - SSE_modelo / SSE_referencia, com a referencia sendo a media EXPANSIVEL
    do proprio fluxo — o chute honesto de quem so conhece o passado. Nao e a
    media da amostra cheia, que ja seria look-ahead. Pode ser negativo: e o que
    acontece quando o modelo erra mais do que o chute da media.
    """
    y = np.asarray(realizado, dtype=float)
    p = np.asarray(previsto, dtype=float)
    ok = ~(np.isnan(y) | np.isnan(p))
    y, p = y[ok], p[ok]
    if len(y) < 2:
        return float("nan")

    ref = pd.Series(y).expanding().mean().shift(1).to_numpy()
    ref[0] = 0.0

    sse_modelo = np.nansum((y - p) ** 2)
    sse_ref = np.nansum((y - ref) ** 2)
    if sse_ref == 0:
        return float("nan")
    return float(1 - sse_modelo / sse_ref)


def previsao_oos(painel: pd.DataFrame, spec: Spec, min_treino: int = 252) -> pd.DataFrame:
    """Previsao em t com coeficientes ajustados so ate t-1.

    Reajusta intercepto e beta a cada passo, em janela expansivel. E lento (uma
    OLS por dia), mas a amostra tem ~1.000 linhas e a clareza vale mais que o
    tempo aqui.
    """
    x = serie_preditora(painel, spec).to_numpy()
    y = painel[spec.alvo].to_numpy()
    valido = ~(np.isnan(x) | np.isnan(y))

    previsto = np.full(len(painel), np.nan)
    for i in range(len(painel)):
        if not valido[i]:
            continue
        sel = valido.copy()
        sel[i:] = False  # so o passado estrito
        if sel.sum() < min_treino:
            continue
        m = sm.OLS(y[sel], sm.add_constant(x[sel])).fit()
        previsto[i] = float(m.params[0] + m.params[1] * x[i])

    return pd.DataFrame({
        "Data": painel["Data"].to_numpy(),
        "realizado": np.where(valido, y, np.nan),
        "previsto": previsto,
    })


def _ols_simples(painel: pd.DataFrame, spec: Spec) -> dict:
    x = serie_preditora(painel, spec)
    d = pd.DataFrame({"y": painel[spec.alvo], "x": x}).dropna()
    if len(d) < 30:
        return {"beta": float("nan"), "tstat": float("nan"), "r2": float("nan"), "nobs": len(d)}
    m = sm.OLS(d["y"], sm.add_constant(d["x"])).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
    return {
        "beta": float(m.params.iloc[1]),
        "tstat": float(m.tvalues.iloc[1]),
        "r2": float(m.rsquared),
        "nobs": len(d),
    }


def avaliar(painel: pd.DataFrame, spec: Spec, min_treino: int = 252) -> dict:
    """R2 fora de amostra, correlacao, erro em USD mm e split de amostra.

    O erro em USD mm esta aqui de proposito ao lado do R2: o R2 diz se ha
    relacao, o erro em USD mm diz se ela e grande o bastante para significar
    alguma coisa numa mesa.
    """
    p = previsao_oos(painel, spec, min_treino=min_treino).dropna(
        subset=["realizado", "previsto"]
    )

    meio = len(painel) // 2
    metades = {
        "primeira": _ols_simples(painel.iloc[:meio], spec),
        "segunda": _ols_simples(painel.iloc[meio:], spec),
    }

    if p.empty:
        return {"r2_oos": float("nan"), "corr": float("nan"),
                "mae_usd_mm": float("nan"), "nobs": 0, "metades": metades}

    return {
        "r2_oos": r2_oos(p["realizado"].to_numpy(), p["previsto"].to_numpy()),
        "corr": float(p["realizado"].corr(p["previsto"])),
        "mae_usd_mm": float((p["realizado"] - p["previsto"]).abs().mean()),
        "nobs": len(p),
        "metades": metades,
    }


def tem_plateau(tabela: pd.DataFrame, tipo: str, n: int, aval_por_spec: dict) -> tuple[bool, str]:
    """A vencedora nao pode ser um pico isolado na grade.

    Um rebalanceamento real produz estrutura de defasagem suave: se o AFP ajusta
    o hedge ao longo de alguns dias, k=3 funcionar implica k=2 e k=4 funcionarem.
    Vencedor cercado de vizinhos mortos e a assinatura do ruido, e e exatamente o
    que a busca por especificacao produz numa amostra de 1.054 observacoes.

    Criterio: cada vizinho que existe na grade precisa ter beta do mesmo sinal e
    r2_oos de pelo menos metade do vencedor.
    """
    alvo = aval_por_spec.get((tipo, n))
    if alvo is None:
        return False, f"especificacao ({tipo}, {n}) sem avaliacao"

    r2_alvo = alvo["r2_oos"]
    sinal = np.sign(alvo["beta"])
    existentes = set(tabela[tabela["tipo"] == tipo]["n"].tolist())

    vizinhos = [v for v in (n - 1, n + 1) if v in existentes]
    if not vizinhos:
        return False, f"({tipo}, {n}) nao tem vizinho na grade para sustentar plateau"

    for v in vizinhos:
        a = aval_por_spec.get((tipo, v))
        if a is None:
            return False, f"vizinho ({tipo}, {v}) sem avaliacao"
        if np.sign(a["beta"]) != sinal:
            return False, (
                f"vizinho ({tipo}, {v}) tem beta de sinal oposto "
                f"({a['beta']:,.0f} vs {alvo['beta']:,.0f})"
            )
        if a["r2_oos"] < r2_alvo / 2:
            return False, (
                f"vizinho ({tipo}, {v}) tem R2 OOS {a['r2_oos']:.3f}, "
                f"menos da metade do vencedor ({r2_alvo:.3f}) — pico isolado"
            )

    return True, f"plateau confirmado com os vizinhos {vizinhos}"
```

- [ ] **Step 4: Rodar os testes e confirmar que passam**

Run: `python -m pytest tests/afp_leading -v`
Expected: PASS, 19 testes no total

- [ ] **Step 5: Commit**

```bash
git add estudos/afp_leading/avaliacao.py tests/afp_leading/test_avaliacao.py
git commit -m "estudo AFP: avaliacao fora de amostra e teste de plateau

R2 OOS contra a media expansivel (Campbell-Thompson), previsao com coeficientes
so do passado estrito, e o criterio de plateau que rejeita vencedor de grade sem
vizinhos vivos — a defesa contra a busca numa amostra que nao cresce."
```

---

### Task 5: Relatório e entrypoint

**Files:**
- Create: `estudos/afp_leading/relatorio.py`
- Create: `estudos/afp_leading/rodar.py`

**Interfaces:**
- Consumes: tudo das tasks 1–4
- Produces: `estudos/afp_leading/saida/afp_fluxo_previsto.html`

**Esta task não tem teste unitário** — é orquestração e apresentação. O teste é a execução de ponta a ponta no Step 4, contra o dado real. Não invente asserts sobre o resultado: **o valor do estudo é o número que sair, seja ele qual for.**

- [ ] **Step 1: Implementar `relatorio.py`**

`estudos/afp_leading/relatorio.py`:

```python
"""Relatorio HTML do estudo, no tema do painel."""
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from chart_builder import JGP_VERDE, JGP_PRETO, JGP_AZUL  # noqa: E402


def _fig_estrutura(tab: pd.DataFrame, tipo: str, titulo: str) -> str:
    d = tab[tab["tipo"] == tipo].sort_values("n")
    cores = [JGP_AZUL if u else "#C9C9C4" for u in d["utilizavel"]]
    fig = go.Figure(go.Bar(
        x=d["n"], y=d["r2"], marker_color=cores,
        hovertemplate="n=%{x}<br>R2=%{y:.3f}<extra></extra>",
    ))
    fig.update_layout(
        title=titulo, template="jgp", height=340,
        margin=dict(l=60, r=20, t=64, b=60),
        xaxis_title="defasagem (pregoes)", yaxis_title="R2 dentro de amostra",
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)


def _fig_beta(bm: pd.DataFrame) -> str:
    d = bm.dropna(subset=["beta"])
    fig = go.Figure(go.Scatter(
        x=d["Data"], y=-d["beta"] / 1000.0, mode="lines",
        line=dict(color=JGP_VERDE, width=1.5),
    ))
    fig.update_layout(
        title="Exposicao hedgeada implicita (h*A), janela expansivel",
        template="jgp", height=360, margin=dict(l=60, r=20, t=64, b=60),
        yaxis_title="USD bilhoes",
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)


def _fig_previsto(p: pd.DataFrame) -> str:
    d = p.dropna(subset=["realizado", "previsto"])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d["Data"], y=d["realizado"], mode="lines",
                             name="realizado", line=dict(color=JGP_PRETO, width=1)))
    fig.add_trace(go.Scatter(x=d["Data"], y=d["previsto"], mode="lines",
                             name="previsto", line=dict(color=JGP_VERDE, width=1.5)))
    fig.update_layout(
        title="Fluxo AFP: previsto fora de amostra vs realizado",
        template="jgp", height=400, margin=dict(l=60, r=20, t=64, b=96),
        yaxis_title="USD milhoes (+ compra de USD)",
        legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="left", x=0),
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)


def _tabela_decisao(criterios: list[tuple[str, bool, str]]) -> str:
    linhas = []
    for nome, ok, detalhe in criterios:
        marca = "PASSOU" if ok else "FALHOU"
        cor = JGP_VERDE if ok else "#E63946"
        linhas.append(
            f"<tr><td>{nome}</td>"
            f"<td style='color:{cor};font-weight:700'>{marca}</td>"
            f"<td>{detalhe}</td></tr>"
        )
    return (
        "<table class='data-table'><thead><tr>"
        "<th>Criterio</th><th>Resultado</th><th>Detalhe</th>"
        "</tr></thead><tbody>" + "".join(linhas) + "</tbody></table>"
    )


def gerar(
    caminho: Path,
    spec,
    tab: pd.DataFrame,
    bm: pd.DataFrame,
    prev: pd.DataFrame,
    aval: dict,
    criterios: list[tuple[str, bool, str]],
    veredito: bool,
) -> Path:
    """Escreve o HTML. Nao decide nada: so mostra o que as outras pecas mediram."""
    titulo_veredito = (
        "RESULTADO POSITIVO: a hipotese sobreviveu"
        if veredito else
        "RESULTADO NEGATIVO: a hipotese nao passou"
    )
    m = aval["metades"]
    corpo = f"""
<h2>Veredito</h2>
<p class="lead"><b>{titulo_veredito}</b></p>
<p class="sub">Especificacao vencedora: alvo <code>{spec.alvo}</code>,
preditor <code>{spec.preditor}</code>, {spec.tipo} n={spec.n}.
R2 fora de amostra {aval['r2_oos']:.3f} em {aval['nobs']} observacoes,
correlacao {aval['corr']:.3f}, erro absoluto medio de
USD {aval['mae_usd_mm']:,.0f} mm.</p>
<div class="card">{_tabela_decisao(criterios)}</div>

<h2>Estrutura de defasagem</h2>
<p class="sub">Cinza = nao utilizavel. O MXWO fecha depois do mercado cambial
chileno, entao o retorno do mesmo dia (k=0) nao estaria disponivel a tempo.</p>
<div class="card">{_fig_estrutura(tab, 'pontual', 'Defasagem pontual: R2 por k')}</div>
<div class="card">{_fig_estrutura(tab, 'acumulada', 'Janela acumulada: R2 por w')}</div>

<h2>Estabilidade do beta</h2>
<div class="card">{_fig_beta(bm)}</div>

<h2>Previsto vs realizado</h2>
<p class="sub">Previsao em cada dia usa coeficientes ajustados apenas com dado
anterior aquele dia.</p>
<div class="card">{_fig_previsto(prev)}</div>

<h2>Split de amostra</h2>
<div class="card"><table class="data-table">
<thead><tr><th>Metade</th><th>beta</th><th>t-stat</th><th>R2</th><th>n</th></tr></thead>
<tbody>
<tr><td>Primeira</td><td class="num">{m['primeira']['beta']:,.0f}</td>
<td class="num">{m['primeira']['tstat']:.2f}</td>
<td class="num">{m['primeira']['r2']:.3f}</td>
<td class="num">{m['primeira']['nobs']}</td></tr>
<tr><td>Segunda</td><td class="num">{m['segunda']['beta']:,.0f}</td>
<td class="num">{m['segunda']['tstat']:.2f}</td>
<td class="num">{m['segunda']['r2']:.3f}</td>
<td class="num">{m['segunda']['nobs']}</td></tr>
</tbody></table></div>

<h2>Limitacoes</h2>
<p class="sub">1.054 observacoes, e nao ha mais: e o limite do dado do BCCh.
Cada metade do split cobre ~2 anos, entao o teste de estabilidade e tambem um
teste de regime e os dois nao dao para separar. A vencedora foi escolhida entre
~32 especificacoes; o criterio de plateau mitiga a busca, nao a elimina. Nada
aqui tem custo de transacao: e medida de relacao estatistica, nao de P&amp;L.</p>
"""

    html = f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Fluxo AFP previsto &mdash; JGP Macro</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.plot.ly/plotly-2.35.0.min.js"></script>
<style>
:root{{--bg:#F6F4EE;--card:#fff;--ink:#0A0A0A;--ink2:#4A4A48;--ink3:#8C8C88;
--verde:#00B050;--rule:#DDD9CE;--faint:#ECE8DC;--sec:#E4E0D3;--line:#DDD9CE;
--green:#00B050;--green-dark:#008A3F;--chart-title:#1F1F1F;--chart-sub:#666}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:Inter,system-ui,sans-serif;background:var(--bg);color:var(--ink);
font-size:15px;line-height:1.55;padding:2rem clamp(1rem,4vw,4rem) 4rem;max-width:1500px;margin:0 auto}}
h1{{font-size:2.2rem;font-weight:700;letter-spacing:-.028em;margin-bottom:.4rem}}
h2{{counter-increment:s;display:flex;gap:.7rem;align-items:baseline;font-size:1.02rem;
font-weight:600;margin:2rem 0 .9rem;padding-bottom:.5rem;border-bottom:1px dashed var(--rule)}}
h2::before{{content:counter(s,decimal-leading-zero);font-size:.78rem;color:var(--verde);font-weight:600}}
body{{counter-reset:s}}
.lead{{font-size:1rem;color:var(--ink2);margin-bottom:12px}}
.sub{{font-size:12.5px;color:var(--ink3);margin-bottom:12px;line-height:1.6}}
.card{{background:var(--card);border:1px solid var(--faint);padding:.75rem .9rem;margin-bottom:14px}}
table.data-table{{border-collapse:collapse;font-size:12px;width:100%}}
table.data-table th,table.data-table td{{border:1px solid var(--line);padding:5px 10px}}
table.data-table thead th{{background:var(--green);color:#fff;font-weight:700;border-color:var(--green-dark)}}
table.data-table td.num{{text-align:right;font-variant-numeric:tabular-nums}}
code{{background:rgba(0,176,80,.08);padding:1px 4px;font-size:.92em}}
.meta{{font-size:.72rem;text-transform:uppercase;letter-spacing:.1em;color:var(--ink3);margin-bottom:2rem}}
</style></head><body>
<h1>Fluxo AFP previsto a partir de bolsa global</h1>
<div class="meta">JGP Emerging Markets &middot; Chile &middot; gerado em {pd.Timestamp.now():%d/%m/%Y %H:%M}</div>
{corpo}
</body></html>"""

    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(html, encoding="utf-8")
    return caminho
```

- [ ] **Step 2: Implementar `rodar.py`**

`estudos/afp_leading/rodar.py`:

```python
"""Entrypoint do estudo. Encadeia dados -> modelo -> avaliacao -> relatorio.

    python -m estudos.afp_leading.rodar

Escolha da especificacao vencedora: maior R2 fora de amostra entre as
UTILIZAVEIS. Nao a de maior R2 dentro de amostra — dentro de amostra a
especificacao mais flexivel sempre ganha, e o que interessa e prever.
"""
import logging
from pathlib import Path

from .dados import montar_painel
from .modelo import Spec, estrutura_defasagem, beta_movel, portao_sanidade
from .avaliacao import previsao_oos, avaliar, tem_plateau
from .relatorio import gerar

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ALVO = "net_1d"
PREDITOR = "r_MXWO"
SAIDA = Path(__file__).resolve().parent / "saida" / "afp_fluxo_previsto.html"


def main() -> int:
    painel = montar_painel()
    logger.info("Painel com %d observacoes", len(painel))

    tab = estrutura_defasagem(painel, ALVO, PREDITOR)
    utilizaveis = tab[tab["utilizavel"]]
    if utilizaveis.empty:
        raise RuntimeError("nenhuma especificacao utilizavel")

    # Portao de sanidade na melhor candidata dentro de amostra, antes de gastar
    # as ~32 avaliacoes fora de amostra (cada uma roda uma OLS por dia).
    melhor_dentro = utilizaveis.loc[utilizaveis["r2"].idxmax()]
    ok_portao, msg_portao = portao_sanidade(float(melhor_dentro["beta"]))
    logger.info("Portao de sanidade: %s | %s", "OK" if ok_portao else "FALHOU", msg_portao)

    aval_por_spec = {}
    for row in utilizaveis.itertuples():
        a = avaliar(painel, Spec(ALVO, PREDITOR, row.tipo, row.n))
        aval_por_spec[(row.tipo, row.n)] = {"r2_oos": a["r2_oos"], "beta": row.beta, "aval": a}
        logger.info("%s n=%d: beta %.0f, R2 OOS %.3f", row.tipo, row.n, row.beta, a["r2_oos"])

    (tipo_v, n_v) = max(aval_por_spec, key=lambda k: aval_por_spec[k]["r2_oos"])
    spec = Spec(ALVO, PREDITOR, tipo_v, n_v)
    aval = aval_por_spec[(tipo_v, n_v)]["aval"]
    logger.info("Vencedora: %s n=%d, R2 OOS %.3f", tipo_v, n_v, aval["r2_oos"])

    ok_plateau, msg_plateau = tem_plateau(tab, tipo_v, n_v, aval_por_spec)
    m = aval["metades"]
    b1, b2 = m["primeira"]["beta"], m["segunda"]["beta"]
    mesmo_sinal = (b1 < 0) == (b2 < 0)
    razao = max(abs(b1), abs(b2)) / min(abs(b1), abs(b2)) if min(abs(b1), abs(b2)) > 0 else float("inf")
    ok_estabilidade = mesmo_sinal and razao <= 2.0
    ok_r2 = aval["r2_oos"] > 0.10

    criterios = [
        ("1. Portao de sanidade (beta negativo, h*A plausivel)", ok_portao, msg_portao),
        ("2. R2 fora de amostra > 0,10", ok_r2, f"R2 OOS = {aval['r2_oos']:.3f}"),
        ("3. Estabilidade nas duas metades (mesmo sinal, razao <= 2x)", ok_estabilidade,
         f"beta {b1:,.0f} e {b2:,.0f}, razao {razao:.2f}x"),
        ("4. Plateau (vizinhos vivos na grade)", ok_plateau, msg_plateau),
    ]
    veredito = all(ok for _, ok, _ in criterios)

    bm = beta_movel(painel, spec)
    prev = previsao_oos(painel, spec)
    caminho = gerar(SAIDA, spec, tab, bm, prev, aval, criterios, veredito)

    logger.info("VEREDITO: %s", "POSITIVO" if veredito else "NEGATIVO")
    logger.info("Relatorio em %s", caminho)
    return 0 if veredito else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Rodar o estudo de ponta a ponta**

Run: `python -m estudos.afp_leading.rodar`

Expected: log com o portão de sanidade, uma linha por especificação utilizável, a vencedora, os quatro critérios e o veredito. Sai com código 0 (positivo) ou 1 (negativo). O HTML aparece em `estudos/afp_leading/saida/afp_fluxo_previsto.html`.

**Os dois vereditos são resultados válidos.** Não ajuste parâmetro nenhum para virar um negativo em positivo — o critério foi fixado no spec antes de rodar, exatamente para isso. Se o portão de sanidade falhar (β̂ positivo), pare e reporte: a hipótese está errada.

- [ ] **Step 4: Conferir o HTML no navegador**

Run: `python -c "import webbrowser,pathlib; webbrowser.open(pathlib.Path('estudos/afp_leading/saida/afp_fluxo_previsto.html').resolve().as_uri())"`

Verificar: os quatro gráficos renderizam, a tabela de decisão mostra os quatro critérios, e os números do texto batem com os do log.

- [ ] **Step 5: Ignorar a saída no git e commitar**

Acrescentar a `.gitignore`:

```
estudos/*/saida/
```

```bash
git add .gitignore estudos/afp_leading/relatorio.py estudos/afp_leading/rodar.py
git commit -m "estudo AFP: relatorio HTML e entrypoint

Vencedora escolhida por maior R2 FORA de amostra entre as utilizaveis, nao por
R2 dentro de amostra. Os quatro criterios do spec sao avaliados e impressos na
tabela de decisao; o exit code segue o veredito. Saida HTML fora do git."
```

---

## Self-review

**Cobertura do spec:**

| Requisito do spec | Task |
|---|---|
| Painel diário alinhado, sem ffill no fluxo | 1 |
| Alvo `ndf_1d` e `net_1d` separados | 1 (colunas), 5 (`ALVO` trocável) |
| Preditores MXWO/MXWD/SPX/MXEF | 1 |
| Estrutura de defasagem, 11 pontuais + 21 acumuladas | 2 |
| Newey-West com defasagem acompanhando a janela | 2 |
| `k=0` marcado não utilizável | 2 |
| β em janela móvel sem look-ahead | 3 |
| Portão de sanidade (sinal + faixa 5–90 bi) | 3 |
| R² fora de amostra | 4 |
| Correlação e erro em USD mm | 4 |
| Split em duas metades | 4 |
| Critério de plateau | 4 |
| Relatório HTML padrão JGP | 5 |
| Os quatro critérios de sucesso avaliados | 5 |
| Limitações no relatório | 5 |

**Nota de escopo:** o spec pede os dois alvos (`ndf_1d` e `net_1d`) modelados separadamente. O `rodar.py` roda `net_1d` por padrão; rodar `ndf_1d` é trocar a constante `ALVO`. Se a comparação entre os dois for central para a leitura do resultado, vale um passo extra depois do Step 3 rodando as duas e comparando — mas isso é análise, não código novo, e o plano não o força.

**Consistência de tipos:** `Spec` tem os mesmos quatro campos em todas as tasks; `serie_preditora`, `beta_movel`, `previsao_oos` e `avaliar` recebem `(painel, spec, ...)` na mesma ordem; `aval_por_spec` é sempre `dict[(tipo, n)] -> {"r2_oos", "beta", ...}`, mesmo formato que `tem_plateau` consome nos testes e em `rodar.py`.
