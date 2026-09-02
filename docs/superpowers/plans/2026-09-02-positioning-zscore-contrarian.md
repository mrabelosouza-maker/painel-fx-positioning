# Níveis esticados de positioning como sinal contrarian — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Medir se um nível esticado de positioning cambial chileno (z-score rolante de 252 pregões) antecipa reversão do USDCLP, e reportar o resultado com falsificação suficiente para que um "não sei" seja uma conclusão legítima.

**Architecture:** Módulo de pesquisa offline em `estudos/positioning_zscore/`, quatro peças com uma responsabilidade cada: `dados.py` (rede + convenção de sinal + z + retornos forward), `buckets.py` (atribuição de bucket, agregação, block bootstrap), `falsificacao.py` (placebo, espelho contábil, veredito), `relatorio.py` (só formata). A única alteração em `src/` é a função `rolling_zscore` em `data_processor.py`, colocada lá porque a fase 2 (gráficos de z-score no painel) vai reusá-la.

**Tech Stack:** Python 3.11, pandas, numpy, plotly. **Nenhuma dependência nova** — sem scipy, sem statsmodels. Correlação de Spearman e block bootstrap são doze linhas de numpy cada; adicionar dependência para isso não se paga.

## Global Constraints

- Branch nova a partir da `main`. Não mergear, rebasear ou tocar em `estudo-afp-leading` nem `pregoes-tudo`.
- Sem dependência nova. Se algo parecer exigir scipy, escreva em numpy.
- Toda aleatoriedade recebe semente explícita. `SEED = 20260902`. Rodar duas vezes tem de dar o mesmo número.
- `dados.py` é o único módulo que toca a rede. Os outros recebem DataFrame pronto, para serem testáveis sem BCCh.
- Convenção de sinal: **acima de zero = comprando USD**. Vale para todas as séries do estudo.
- Retorno forward positivo = **CLP depreciou**.
- Nada de look-ahead: `z[t]` só usa dado até `t`. Existe teste para isso e ele não é opcional.
- `relatorio.py` não calcula nada. Se você precisar de um número novo no HTML, ele vem calculado de outro módulo.
- Comentários e docstrings em português, sem acento em código (segue o padrão de `src/`). Texto do HTML pode ter acento.
- Horizontes fixos: `HORIZONTES = (5, 21, 63)` pregões.
- Buckets fixos, nunca derivados do dado: `z < -2`, `-2 <= z < -1`, `-1 <= z <= 1`, `1 < z <= 2`, `z > 2`.

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `src/data_processor.py` (modificar) | `rolling_zscore` — peça compartilhada com a fase 2 |
| `estudos/__init__.py` (criar, vazio) | pacote |
| `estudos/positioning_zscore/__init__.py` (criar, vazio) | pacote |
| `estudos/positioning_zscore/dados.py` | rede, convenção de sinal, z, retornos forward; devolve painel longo |
| `estudos/positioning_zscore/buckets.py` | bucket, episódios, block bootstrap, tabela de resultados |
| `estudos/positioning_zscore/falsificacao.py` | placebo, espelho contábil, rótulo de anedota, veredito |
| `estudos/positioning_zscore/relatorio.py` | HTML; só formata |
| `estudos/positioning_zscore/rodar.py` | entrypoint que encadeia tudo |
| `estudos/positioning_zscore/saida/` | destino do HTML (criado em runtime) |
| `tests/__init__.py`, `tests/positioning_zscore/__init__.py` (criar, vazios) | pacote |
| `tests/test_data_processor.py` | testes de `rolling_zscore` |
| `tests/positioning_zscore/test_dados.py` | convenção, alinhamento de retorno, formato do painel |
| `tests/positioning_zscore/test_buckets.py` | bordas de bucket, episódios, bootstrap |
| `tests/positioning_zscore/test_falsificacao.py` | placebo, espelho, veredito |
| `tests/positioning_zscore/test_relatorio.py` | smoke: escreve arquivo com seções esperadas |
| `pytest.ini` (criar) | config |

**Desvio do spec, deliberado:** o spec dizia `__main__.py` como entrypoint. Uso `rodar.py`, que é o nome já usado por `estudos/afp_leading/rodar.py`. Seguir a convenção do repo vale mais que seguir a letra do spec.

---

### Task 0: Branch e scaffolding

**Files:**
- Create: `estudos/__init__.py`, `estudos/positioning_zscore/__init__.py`, `tests/__init__.py`, `tests/positioning_zscore/__init__.py`, `pytest.ini`

**Interfaces:**
- Consumes: nada
- Produces: pacotes importáveis e `pytest` funcionando na `main`

- [ ] **Step 1: Criar a branch a partir da main**

```bash
git checkout main
git status --short
```

Esperado: só arquivos untracked (`Painel_Positioning.Rmd`, `positioning_moedaestrangeira.R`, `test.py`, `update_log.txt`, `estudos/`). Se houver `M` em qualquer arquivo rastreado, **pare** e pergunte — há trabalho não commitado de outra sessão.

```bash
git checkout -b positioning-zscore
```

- [ ] **Step 2: Criar os arquivos de pacote e o pytest.ini**

Os quatro `__init__.py` são **vazios** (zero bytes). Note que `estudos/` já existe no disco como diretório untracked com `__pycache__/` e `saida/` de outra branch — criar o `__init__.py` dentro dele é o certo, não apague o diretório.

`pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -q
```

- [ ] **Step 3: Confirmar que o pytest roda e não coleta nada ainda**

Run: `python -m pytest`
Expected: `no tests ran` (exit code 5). Não é erro — é a suíte vazia.

- [ ] **Step 4: Commit**

```bash
git add estudos/__init__.py estudos/positioning_zscore/__init__.py tests/__init__.py tests/positioning_zscore/__init__.py pytest.ini
git commit -m "Scaffolding de estudo e testes na main"
```

---

### Task 1: `rolling_zscore` em `src/data_processor.py`

**Files:**
- Modify: `src/data_processor.py` (adicionar função nova ao fim da seção FX Positioning, logo depois de `compute_deltas`)
- Test: `tests/test_data_processor.py`

**Interfaces:**
- Consumes: nada
- Produces: `rolling_zscore(serie: pd.Series, janela: int = 252, min_obs: int = 200, eps: float = 1e-9) -> pd.Series` — devolve Series de mesmo índice, com NaN no burn-in e onde a janela for pobre ou degenerada.

- [ ] **Step 1: Escrever os testes que falham**

Criar `tests/test_data_processor.py`:

```python
"""Testes de data_processor: por ora, so o z-score rolante."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from data_processor import rolling_zscore  # noqa: E402


def test_valor_bate_com_calculo_manual():
    # Janela de 4: o primeiro z valido e no indice 3, sobre [1, 2, 3, 10].
    s = pd.Series([1.0, 2.0, 3.0, 10.0, 4.0])
    z = rolling_zscore(s, janela=4, min_obs=4)

    janela = np.array([1.0, 2.0, 3.0, 10.0])
    esperado = (10.0 - janela.mean()) / janela.std(ddof=1)
    assert z.iloc[3] == pytest.approx(esperado)


def test_burn_in_exige_janela_cheia_nao_apenas_min_obs():
    # min_obs menor que a janela nao antecipa o primeiro valor: o span tem
    # de estar completo. Com janela=252, os 251 primeiros sao NaN.
    s = pd.Series(np.arange(300, dtype=float))
    z = rolling_zscore(s, janela=252, min_obs=200)

    assert z.iloc[:251].isna().all()
    assert z.notna().iloc[251]


def test_desvio_nulo_devolve_nan_em_vez_de_inf():
    s = pd.Series([5.0] * 10)
    z = rolling_zscore(s, janela=4, min_obs=4)
    assert z.isna().all()
    assert not np.isinf(z.to_numpy(dtype=float)).any()


def test_janela_pobre_de_observacoes_validas_devolve_nan():
    # Janela cheia de span, mas so 2 valores validos dentro dela, e min_obs=3.
    s = pd.Series([1.0, np.nan, np.nan, 2.0, 3.0, np.nan, np.nan, 4.0])
    z = rolling_zscore(s, janela=4, min_obs=3)
    # Indice 4: janela [nan, nan, 2, 3] -> 2 validos < 3 -> NaN
    assert pd.isna(z.iloc[4])
    # Indice 3 esta no burn-in (janela-1 = 3) -> NaN de todo modo
    assert pd.isna(z.iloc[3])


def test_sem_vazamento_dado_futuro_nao_muda_z_passado():
    base = pd.Series(np.linspace(0.0, 10.0, 60))
    z_base = rolling_zscore(base, janela=10, min_obs=10)

    adulterada = base.copy()
    adulterada.iloc[40:] = 999.0          # mexe so no futuro
    z_adulterada = rolling_zscore(adulterada, janela=10, min_obs=10)

    pd.testing.assert_series_equal(z_base.iloc[:40], z_adulterada.iloc[:40])


def test_preserva_indice_e_nome():
    idx = pd.date_range("2022-01-03", periods=20, freq="B")
    s = pd.Series(np.arange(20, dtype=float), index=idx, name="Offshore")
    z = rolling_zscore(s, janela=5, min_obs=5)
    assert z.index.equals(idx)
    assert z.name == "Offshore"
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `python -m pytest tests/test_data_processor.py -v`
Expected: FAIL na coleta — `ImportError: cannot import name 'rolling_zscore' from 'data_processor'`.

- [ ] **Step 3: Implementar**

Em `src/data_processor.py`, adicionar depois de `compute_deltas` (procure o fim daquela função, antes da próxima seção com barra de comentário):

```python
def rolling_zscore(
    serie: pd.Series, janela: int = 252, min_obs: int = 200,
    eps: float = 1e-9,
) -> pd.Series:
    """Z-score de janela rolante, calculado POINT-IN-TIME.

    A janela fecha em t e inclui o proprio serie[t]. Nada posterior a t entra:
    e essa propriedade que torna o z utilizavel como sinal, e nao apenas como
    escala de leitura. Existe teste que adultera o futuro e confirma que o
    passado nao se move.

    Tres bordas, todas resolvidas em NaN e nenhuma em numero inventado:

    - Burn-in: exige-se o span CHEIO, nao apenas `min_obs` observacoes. Com
      janela=252 os 251 primeiros pregoes saem NaN. Sem isso o inicio da
      amostra ganharia z calculado sobre meia janela, que nao e comparavel ao
      resto da serie.
    - Janela pobre: dentro do span cheio, exige-se `min_obs` valores validos.
      Feriado do BCCh sem publicacao abre buraco na serie; abaixo desse minimo
      a media e o desvio sao estimados em amostra rala e o z e ruido.
    - Desvio degenerado: desvio abaixo de `eps` devolve NaN em vez de dividir
      por quase-zero e imprimir z na casa dos milhares.
    """
    janelas = serie.rolling(window=janela, min_periods=min_obs)
    media = janelas.mean()
    desvio = janelas.std(ddof=1)

    z = (serie - media) / desvio.where(desvio > eps)
    if janela > 1:
        z.iloc[: janela - 1] = np.nan
    return z
```

Confirme que `numpy as np` e `pandas as pd` já estão importados no topo do arquivo (estão — `compute_deltas` usa os dois).

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `python -m pytest tests/test_data_processor.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/data_processor.py tests/test_data_processor.py
git commit -m "Z-score rolante point-in-time em data_processor"
```

---

### Task 2: `dados.py` — painel longo com z e retornos forward

**Files:**
- Create: `estudos/positioning_zscore/dados.py`
- Test: `tests/positioning_zscore/test_dados.py`

**Interfaces:**
- Consumes: `rolling_zscore` da Task 1; `data_processor.build_fx_dados()` do painel
- Produces:
  - `SERIES: dict[str, tuple[str, int]]` — nome no estudo → (coluna do BCCh, sinal)
  - `HORIZONTES: tuple[int, ...]` = `(5, 21, 63)`
  - `JANELA_Z: int` = `252`
  - `aplicar_convencao(dados: pd.DataFrame) -> pd.DataFrame` — devolve wide com `Data`, `USDCLP` e uma coluna por série do estudo, todas em compra-de-USD
  - `retornos_forward(usdclp: pd.Series, horizontes=HORIZONTES) -> pd.DataFrame` — colunas `r_5`, `r_21`, `r_63`
  - `montar_painel(dados: pd.DataFrame | None = None) -> pd.DataFrame` — painel LONGO com colunas `Data`, `serie`, `nivel`, `z`, `r_5`, `r_21`, `r_63`. Com `dados=None` busca da rede.

- [ ] **Step 1: Escrever os testes que falham**

Criar `tests/positioning_zscore/test_dados.py`:

```python
"""Testes do painel do estudo: convencao de sinal, z e retorno forward."""
import numpy as np
import pandas as pd
import pytest

from estudos.positioning_zscore.dados import (
    HORIZONTES, SERIES, aplicar_convencao, montar_painel, retornos_forward,
)


def _dados_falsos(n=400):
    """Imita a saida de build_fx_dados: wide, uma linha por pregao."""
    idx = pd.date_range("2022-01-03", periods=n, freq="B")
    rng = np.random.default_rng(7)
    return pd.DataFrame({
        "Data": idx,
        "No residentes": rng.normal(0, 100, n).cumsum(),
        "Fondos de pensiones": rng.normal(0, 100, n).cumsum(),
        "Empresas sector real": rng.normal(0, 100, n).cumsum(),
        "PosicaoBancos": rng.normal(0, 100, n).cumsum(),
        "USDCLP": 900 + rng.normal(0, 5, n).cumsum(),
    })


def test_convencao_inverte_pensao_e_offshore_e_preserva_os_outros():
    d = _dados_falsos()
    w = aplicar_convencao(d)

    assert w["Fundos de Pensão"].iloc[0] == pytest.approx(-d["Fondos de pensiones"].iloc[0])
    assert w["Offshore"].iloc[0] == pytest.approx(-d["No residentes"].iloc[0])
    assert w["Corporate"].iloc[0] == pytest.approx(d["Empresas sector real"].iloc[0])
    assert w["Bancos"].iloc[0] == pytest.approx(d["PosicaoBancos"].iloc[0])


def test_total_e_a_soma_das_duas_pernas_ja_invertidas():
    d = _dados_falsos()
    w = aplicar_convencao(d)
    esperado = w["Fundos de Pensão"] + w["Offshore"]
    pd.testing.assert_series_equal(
        w["Total (Pensões + Offshore)"], esperado, check_names=False,
    )


def test_retorno_forward_alinha_h_pregoes_a_frente():
    usdclp = pd.Series([100.0, 110.0, 121.0, 133.1])
    r = retornos_forward(usdclp, horizontes=(1,))
    # r_1[0] = 100 * ln(110/100)
    assert r["r_1"].iloc[0] == pytest.approx(100 * np.log(1.1))
    assert r["r_1"].iloc[1] == pytest.approx(100 * np.log(1.1))


def test_retorno_forward_e_nan_nas_ultimas_h_linhas():
    usdclp = pd.Series(np.linspace(900, 1000, 50))
    r = retornos_forward(usdclp, horizontes=(5, 21))
    assert r["r_5"].iloc[-5:].isna().all()
    assert r["r_5"].notna().iloc[-6]
    assert r["r_21"].iloc[-21:].isna().all()


def test_retorno_positivo_significa_clp_depreciando():
    usdclp = pd.Series([900.0, 950.0])   # USDCLP subiu -> CLP depreciou
    r = retornos_forward(usdclp, horizontes=(1,))
    assert r["r_1"].iloc[0] > 0


def test_painel_longo_tem_uma_linha_por_serie_e_data():
    d = _dados_falsos(n=400)
    p = montar_painel(d)

    assert set(p.columns) == {"Data", "serie", "nivel", "z",
                              *[f"r_{h}" for h in HORIZONTES]}
    esperado = len(SERIES) + 1          # as series individuais mais o Total
    assert p["serie"].nunique() == esperado
    assert len(p) == esperado * len(d)


def test_painel_nao_tem_z_no_burn_in():
    d = _dados_falsos(n=400)
    p = montar_painel(d)
    primeiras = p[p["Data"].isin(d["Data"].iloc[:251])]
    assert primeiras["z"].isna().all()


def test_montar_painel_nao_altera_o_dataframe_recebido():
    d = _dados_falsos()
    antes = d.copy(deep=True)
    montar_painel(d)
    pd.testing.assert_frame_equal(d, antes)
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `python -m pytest tests/positioning_zscore/test_dados.py -v`
Expected: FAIL na coleta — `ModuleNotFoundError: No module named 'estudos.positioning_zscore.dados'`.

- [ ] **Step 3: Implementar**

Criar `estudos/positioning_zscore/dados.py`:

```python
"""Painel do estudo: nivel de positioning, z-score e retorno forward do USDCLP.

Unico modulo do estudo que toca a rede. Os demais recebem DataFrame pronto,
para poderem ser testados sem BCCh.
"""
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from data_processor import build_fx_dados, rolling_zscore  # noqa: E402

logger = logging.getLogger(__name__)

# Nome no estudo -> (coluna do BCCh, sinal para virar compra-de-USD).
#
# A serie crua do BCCh vem na otica do banco residente: positivo = o setor esta
# net short USD, isto e, VENDENDO USD. Pensao e Offshore entram invertidas para
# ficarem em compra-de-USD, exatamente como as abas do painel. Corporate e
# Bancos ficam no sinal cru — e a mesma escolha que o painel faz.
SERIES = {
    "Fundos de Pensão": ("Fondos de pensiones", -1),
    "Offshore": ("No residentes", -1),
    "Corporate": ("Empresas sector real", 1),
    "Bancos": ("PosicaoBancos", 1),
}

# O agregado das duas pernas especulativas, ja invertidas.
NOME_TOTAL = "Total (Pensões + Offshore)"
PERNAS_TOTAL = ("Fundos de Pensão", "Offshore")

HORIZONTES = (5, 21, 63)
JANELA_Z = 252
MIN_OBS_Z = 200


def aplicar_convencao(dados: pd.DataFrame) -> pd.DataFrame:
    """Traduz o wide do painel para compra-de-USD, mais o agregado.

    Devolve DataFrame novo; nao altera `dados`.
    """
    saida = pd.DataFrame({"Data": dados["Data"].to_numpy()})
    for nome, (coluna, sinal) in SERIES.items():
        saida[nome] = sinal * dados[coluna].to_numpy(dtype=float)
    saida[NOME_TOTAL] = sum(saida[p] for p in PERNAS_TOTAL)
    saida["USDCLP"] = dados["USDCLP"].to_numpy(dtype=float)
    return saida


def retornos_forward(
    usdclp: pd.Series, horizontes=HORIZONTES,
) -> pd.DataFrame:
    """Retorno log do USDCLP h pregoes A FRENTE, em pontos percentuais.

    Positivo = USDCLP subiu = CLP depreciou. As ultimas h linhas ficam NaN e
    assim permanecem: preencher seria inventar o retorno que ainda nao ocorreu.
    """
    ln = np.log(usdclp.astype(float))
    return pd.DataFrame(
        {f"r_{h}": 100.0 * (ln.shift(-h) - ln) for h in horizontes},
        index=usdclp.index,
    )


def montar_painel(dados: pd.DataFrame | None = None) -> pd.DataFrame:
    """Painel LONGO: uma linha por (serie, data).

    Formato longo de proposito: o resto do estudo agrupa por serie e por bucket,
    e agrupar em longo e uma linha de codigo em vez de um laco sobre colunas.
    """
    if dados is None:
        logger.info("Buscando dados FX do BCCh...")
        dados = build_fx_dados()

    wide = aplicar_convencao(dados)
    ret = retornos_forward(wide["USDCLP"])
    cols_r = list(ret.columns)

    nomes = [*SERIES.keys(), NOME_TOTAL]
    pedacos = []
    for nome in nomes:
        bloco = pd.DataFrame({
            "Data": wide["Data"],
            "serie": nome,
            "nivel": wide[nome],
            "z": rolling_zscore(wide[nome], janela=JANELA_Z, min_obs=MIN_OBS_Z),
        })
        for c in cols_r:
            bloco[c] = ret[c]
        pedacos.append(bloco)

    painel = pd.concat(pedacos, ignore_index=True)
    return painel[["Data", "serie", "nivel", "z", *cols_r]]
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `python -m pytest tests/positioning_zscore/test_dados.py -v`
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add estudos/positioning_zscore/dados.py tests/positioning_zscore/test_dados.py
git commit -m "Painel do estudo: convencao de sinal, z e retorno forward"
```

---

### Task 3: `buckets.py` — atribuição e contagem de episódios

**Files:**
- Create: `estudos/positioning_zscore/buckets.py`
- Test: `tests/positioning_zscore/test_buckets.py`

**Interfaces:**
- Consumes: painel longo da Task 2
- Produces:
  - `ORDEM_BUCKETS: tuple[str, ...]` = `("muito_short", "short", "neutro", "long", "muito_long")`
  - `atribuir_bucket(z: pd.Series) -> pd.Series` — dtype object, NaN onde `z` é NaN
  - `contar_episodios(mask: pd.Series) -> int` — número de blocos contíguos de `True`

- [ ] **Step 1: Escrever os testes que falham**

Criar `tests/positioning_zscore/test_buckets.py`:

```python
"""Testes de bucket, episodios e block bootstrap."""
import numpy as np
import pandas as pd
import pytest

from estudos.positioning_zscore.buckets import (
    ORDEM_BUCKETS, atribuir_bucket, contar_episodios,
)


def test_buckets_sao_exaustivos_e_mutuamente_exclusivos():
    z = pd.Series(np.linspace(-5, 5, 1001))
    b = atribuir_bucket(z)
    assert b.notna().all()                       # exaustivo
    assert set(b.unique()) <= set(ORDEM_BUCKETS)  # nenhum rotulo estranho


@pytest.mark.parametrize("valor,esperado", [
    (-3.0, "muito_short"),
    (-2.0001, "muito_short"),
    (-2.0, "short"),        # a borda -2 pertence a short
    (-1.5, "short"),
    (-1.0, "neutro"),       # a borda -1 pertence a neutro
    (0.0, "neutro"),
    (1.0, "neutro"),        # a borda 1 pertence a neutro
    (1.5, "long"),
    (2.0, "long"),          # a borda 2 pertence a long
    (2.0001, "muito_long"),
    (7.0, "muito_long"),
])
def test_bordas_caem_no_bucket_que_a_tabela_declara(valor, esperado):
    b = atribuir_bucket(pd.Series([valor]))
    assert b.iloc[0] == esperado


def test_z_nan_nao_recebe_bucket():
    b = atribuir_bucket(pd.Series([np.nan, 0.0, np.nan]))
    assert pd.isna(b.iloc[0])
    assert b.iloc[1] == "neutro"
    assert pd.isna(b.iloc[2])


def test_contar_episodios_conta_blocos_nao_dias():
    # Dois blocos contiguos, sete dias no total.
    m = pd.Series([False, True, True, True, False, False, True, True, False])
    assert contar_episodios(m) == 2


def test_contar_episodios_bloco_unico_e_serie_vazia():
    assert contar_episodios(pd.Series([True, True, True])) == 1
    assert contar_episodios(pd.Series([False, False])) == 0
    assert contar_episodios(pd.Series([], dtype=bool)) == 0


def test_contar_episodios_nas_bordas_da_serie():
    # Bloco comecando no primeiro dia e outro terminando no ultimo.
    m = pd.Series([True, False, True])
    assert contar_episodios(m) == 2


def test_contar_episodios_trata_nan_como_fora_do_bucket():
    m = pd.Series([True, np.nan, True], dtype=object)
    assert contar_episodios(m) == 2
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `python -m pytest tests/positioning_zscore/test_buckets.py -v`
Expected: FAIL na coleta — `ModuleNotFoundError: No module named 'estudos.positioning_zscore.buckets'`.

- [ ] **Step 3: Implementar**

Criar `estudos/positioning_zscore/buckets.py`:

```python
"""Buckets de z, contagem de episodios e agregacao com block bootstrap."""
import numpy as np
import pandas as pd

# Ordem economica, de vendido a comprado em USD. O resto do estudo depende
# desta ordem para medir monotonicidade da curva dose-resposta.
ORDEM_BUCKETS = ("muito_short", "short", "neutro", "long", "muito_long")

# Faixas FIXAS, definidas antes de olhar o dado. Nao se derivam de quantil da
# amostra: quantil moveria a fronteira junto com o resultado, que e exatamente
# o tipo de escolha a posteriori que este estudo existe para evitar.
CORTES = (-2.0, -1.0, 1.0, 2.0)


def atribuir_bucket(z: pd.Series) -> pd.Series:
    """Rotula cada z. Exaustivo e mutuamente exclusivo por construcao.

    As bordas pertencem ao bucket menos extremo: z = -2 e `short`, nao
    `muito_short`. Escolha arbitraria, mas fixada e testada, para que ninguem
    a mude depois de ver o resultado.
    """
    a, b, c, d = CORTES
    condicoes = [z < a, z < b, z <= c, z <= d, z > d]
    saida = pd.Series(
        np.select(condicoes, list(ORDEM_BUCKETS), default=None),
        index=z.index, dtype=object,
    )
    return saida.where(z.notna())


def contar_episodios(mask: pd.Series) -> int:
    """Numero de blocos contiguos de True — nao o numero de dias.

    E a contagem que importa para saber se ha evidencia: 40 dias seguidos com
    o offshore esticado sao UM episodio, nao 40 observacoes independentes.
    Reportar 40 seria inflar a amostra por um fator de 40.
    """
    m = mask.fillna(False).astype(bool).to_numpy()
    if m.size == 0 or not m.any():
        return 0
    anterior = np.concatenate(([False], m[:-1]))
    return int(np.count_nonzero(m & ~anterior))
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `python -m pytest tests/positioning_zscore/test_buckets.py -v`
Expected: 17 passed (11 do parametrize mais 6).

- [ ] **Step 5: Commit**

```bash
git add estudos/positioning_zscore/buckets.py tests/positioning_zscore/test_buckets.py
git commit -m "Buckets de z e contagem de episodios independentes"
```

---

### Task 4: block bootstrap e tabela de resultados

**Files:**
- Modify: `estudos/positioning_zscore/buckets.py` (adicionar ao fim)
- Modify: `tests/positioning_zscore/test_buckets.py` (adicionar ao fim)

**Interfaces:**
- Consumes: `ORDEM_BUCKETS`, `atribuir_bucket`, `contar_episodios` da Task 3
- Produces:
  - `SEED: int` = `20260902`
  - `block_bootstrap_ic(valores, tamanho_bloco: int, reps: int = 5000, seed: int = SEED, alpha: float = 0.10) -> tuple[float, float]`
  - `resumir(painel: pd.DataFrame, horizontes=(5, 21, 63), reps: int = 5000, seed: int = SEED) -> pd.DataFrame` — colunas `serie`, `horizonte`, `bucket`, `media`, `n_obs`, `n_episodios`, `ic_lo`, `ic_hi`

- [ ] **Step 1: Escrever os testes que falham**

Adicionar ao fim de `tests/positioning_zscore/test_buckets.py`:

```python
from estudos.positioning_zscore.buckets import (  # noqa: E402
    SEED, block_bootstrap_ic, resumir,
)


def test_bootstrap_e_reprodutivel_com_a_mesma_semente():
    v = np.random.default_rng(1).normal(0, 1, 300)
    a = block_bootstrap_ic(v, tamanho_bloco=21, reps=200, seed=SEED)
    b = block_bootstrap_ic(v, tamanho_bloco=21, reps=200, seed=SEED)
    assert a == b


def test_bootstrap_muda_com_semente_diferente():
    v = np.random.default_rng(1).normal(0, 1, 300)
    a = block_bootstrap_ic(v, tamanho_bloco=21, reps=200, seed=1)
    b = block_bootstrap_ic(v, tamanho_bloco=21, reps=200, seed=2)
    assert a != b


def test_ic_contem_a_media_da_amostra():
    v = np.random.default_rng(3).normal(5.0, 1.0, 400)
    lo, hi = block_bootstrap_ic(v, tamanho_bloco=21, reps=500, seed=SEED)
    assert lo < v.mean() < hi


def test_bloco_maior_da_ic_mais_largo_em_serie_autocorrelacionada():
    # AR(1) forte: a sobreposicao entre observacoes vizinhas e o motivo de o
    # bootstrap por blocos existir. Bloco de 1 dia ignora isso e mente estreito.
    rng = np.random.default_rng(11)
    e = rng.normal(0, 1, 2000)
    v = np.zeros(2000)
    for i in range(1, 2000):
        v[i] = 0.95 * v[i - 1] + e[i]

    lo1, hi1 = block_bootstrap_ic(v, tamanho_bloco=1, reps=800, seed=SEED)
    lo50, hi50 = block_bootstrap_ic(v, tamanho_bloco=50, reps=800, seed=SEED)
    assert (hi50 - lo50) > (hi1 - lo1)


def test_bootstrap_com_amostra_vazia_devolve_nan():
    lo, hi = block_bootstrap_ic([], tamanho_bloco=5, reps=10, seed=SEED)
    assert np.isnan(lo) and np.isnan(hi)


def test_bootstrap_ignora_nan():
    v = [1.0, np.nan, 1.0, np.nan, 1.0]
    lo, hi = block_bootstrap_ic(v, tamanho_bloco=2, reps=50, seed=SEED)
    assert lo == pytest.approx(1.0) and hi == pytest.approx(1.0)


def _painel_falso(n=400):
    """Painel longo minimo, duas series, para testar resumir()."""
    idx = pd.date_range("2022-01-03", periods=n, freq="B")
    rng = np.random.default_rng(5)
    pedacos = []
    for nome in ("A", "B"):
        pedacos.append(pd.DataFrame({
            "Data": idx,
            "serie": nome,
            "nivel": rng.normal(0, 1, n).cumsum(),
            "z": rng.normal(0, 1.5, n),
            "r_5": rng.normal(0, 1, n),
            "r_21": rng.normal(0, 2, n),
        }))
    return pd.concat(pedacos, ignore_index=True)


def test_resumir_devolve_uma_linha_por_serie_bucket_horizonte():
    p = _painel_falso()
    r = resumir(p, horizontes=(5, 21), reps=100)

    assert set(r.columns) == {"serie", "horizonte", "bucket", "media",
                              "n_obs", "n_episodios", "ic_lo", "ic_hi"}
    assert set(r["bucket"]) <= set(ORDEM_BUCKETS)
    assert set(r["horizonte"]) == {5, 21}
    assert set(r["serie"]) == {"A", "B"}
    # Nenhuma combinacao serie x horizonte x bucket aparece duas vezes.
    assert not r.duplicated(["serie", "horizonte", "bucket"]).any()
    # Com z ~ N(0, 1.5) e n=400, os cinco buckets aparecem nas duas series.
    assert len(r) == 2 * 2 * 5


def test_resumir_nunca_conta_mais_episodios_que_observacoes():
    p = _painel_falso()
    r = resumir(p, horizontes=(5,), reps=100)
    assert (r["n_episodios"] <= r["n_obs"]).all()


def test_resumir_ignora_linhas_sem_retorno():
    p = _painel_falso(n=300)
    p["bucket_ref"] = atribuir_bucket(p["z"])
    p.loc[p.index[-100:], "r_5"] = np.nan

    r = resumir(p.drop(columns=["bucket_ref"]), horizontes=(5,), reps=100)

    # n_obs soma exatamente as linhas com bucket E retorno definidos.
    esperado = int((p["bucket_ref"].notna() & p["r_5"].notna()).sum())
    assert int(r["n_obs"].sum()) == esperado
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `python -m pytest tests/positioning_zscore/test_buckets.py -v`
Expected: FAIL na coleta — `ImportError: cannot import name 'SEED'`.

- [ ] **Step 3: Implementar**

Adicionar ao fim de `estudos/positioning_zscore/buckets.py`:

```python
# Semente unica do estudo. Rodar duas vezes tem de dar o mesmo numero.
SEED = 20260902


def block_bootstrap_ic(
    valores, tamanho_bloco: int, reps: int = 5000,
    seed: int = SEED, alpha: float = 0.10,
) -> tuple[float, float]:
    """Intervalo de confianca da media por block bootstrap CIRCULAR.

    Por que blocos, e nao bootstrap comum: com horizonte de 63 pregoes, duas
    observacoes vizinhas compartilham 62 dos 63 dias de retorno. Reamostrar
    observacao a observacao trataria isso como informacao independente e
    devolveria intervalo estreito por um fator grande — transformando ruido em
    achado. O bloco preserva a sobreposicao.

    Circular: os blocos dao a volta no fim da amostra, para que toda observacao
    tenha a mesma chance de ser sorteada. Sem isso as pontas entram menos e a
    media reamostrada fica viesada para o meio da amostra.
    """
    v = pd.Series(valores, dtype="float64").dropna().to_numpy()
    n = v.size
    if n == 0:
        return (float("nan"), float("nan"))

    b = int(np.clip(tamanho_bloco, 1, n))
    n_blocos = int(np.ceil(n / b))
    rng = np.random.default_rng(seed)

    inicios = rng.integers(0, n, size=(reps, n_blocos))
    desloc = np.arange(b)
    idx = (inicios[:, :, None] + desloc[None, None, :]) % n
    medias = v[idx.reshape(reps, -1)[:, :n]].mean(axis=1)

    return (
        float(np.quantile(medias, alpha / 2.0)),
        float(np.quantile(medias, 1.0 - alpha / 2.0)),
    )


def resumir(
    painel: pd.DataFrame, horizontes=(5, 21, 63),
    reps: int = 5000, seed: int = SEED,
) -> pd.DataFrame:
    """Tabela de resultados: uma linha por serie x horizonte x bucket.

    O bloco do bootstrap e o proprio horizonte, porque e o horizonte que
    determina quanto duas observacoes vizinhas se sobrepoem.
    """
    p = painel.copy()
    p["bucket"] = atribuir_bucket(p["z"])

    linhas = []
    for serie, dados_serie in p.groupby("serie", sort=False):
        for h in horizontes:
            col = f"r_{h}"
            valido = dados_serie[dados_serie["bucket"].notna()
                                 & dados_serie[col].notna()]
            for bucket in ORDEM_BUCKETS:
                dentro = valido[valido["bucket"] == bucket]
                if dentro.empty:
                    continue
                # Episodios contam sobre o calendario inteiro da serie, nao
                # so sobre as linhas validas: um buraco de retorno no meio de
                # um bloco nao parte o bloco em dois episodios.
                mask = (dados_serie["bucket"] == bucket)
                lo, hi = block_bootstrap_ic(
                    dentro[col], tamanho_bloco=h, reps=reps, seed=seed,
                )
                linhas.append({
                    "serie": serie,
                    "horizonte": h,
                    "bucket": bucket,
                    "media": float(dentro[col].mean()),
                    "n_obs": int(len(dentro)),
                    "n_episodios": contar_episodios(mask),
                    "ic_lo": lo,
                    "ic_hi": hi,
                })

    return pd.DataFrame(linhas)
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `python -m pytest tests/positioning_zscore/test_buckets.py -v`
Expected: todos passam (17 da Task 3 mais 10 novos).

Se `test_resumir_ignora_linhas_sem_retorno` falhar por diferença de contagem, o motivo provável é que `n_obs` já exclui z NaN — ajuste a asserção do teste para comparar com a contagem exata que `resumir` produz, não a implementação.

- [ ] **Step 5: Commit**

```bash
git add estudos/positioning_zscore/buckets.py tests/positioning_zscore/test_buckets.py
git commit -m "Block bootstrap circular e tabela de resultados por bucket"
```

---

### Task 5: `falsificacao.py` — placebo, espelho, veredito

**Files:**
- Create: `estudos/positioning_zscore/falsificacao.py`
- Test: `tests/positioning_zscore/test_falsificacao.py`

**Interfaces:**
- Consumes: painel longo (Task 2), `ORDEM_BUCKETS`/`atribuir_bucket`/`SEED` (Tasks 3-4)
- Produces:
  - `MIN_EPISODIOS: int` = `5`
  - `spread_contrarian(resumo: pd.DataFrame, serie: str, horizonte: int) -> float` — `media(muito_short) - media(muito_long)`
  - `embaralhar_blocos(v: np.ndarray, tamanho_bloco: int, rng) -> np.ndarray`
  - `placebo_blocos(painel, serie: str, horizonte: int, reps: int = 1000, tamanho_bloco: int = 21, seed: int = SEED) -> dict` — chaves `observado`, `p_valor`, `nulo_p05`, `nulo_p95`, `reps`
  - `espelho_contabil(resumo: pd.DataFrame, horizonte: int) -> pd.DataFrame` — colunas `serie_a`, `serie_b`, `correlacao`
  - `rotular_anedota(resumo: pd.DataFrame, min_episodios: int = MIN_EPISODIOS) -> pd.DataFrame` — acrescenta coluna `anedota`
  - `spearman(x, y) -> float`
  - `veredito(resumo, placebos: dict, min_episodios: int = MIN_EPISODIOS) -> tuple[bool, list[dict]]`

- [ ] **Step 1: Escrever os testes que falham**

Criar `tests/positioning_zscore/test_falsificacao.py`:

```python
"""Testes das guardas: placebo, espelho contabil, rotulo e veredito."""
import numpy as np
import pandas as pd
import pytest

from estudos.positioning_zscore.buckets import SEED, resumir
from estudos.positioning_zscore.falsificacao import (
    MIN_EPISODIOS, embaralhar_blocos, espelho_contabil, placebo_blocos,
    rotular_anedota, spearman, spread_contrarian, veredito,
)


def _resumo_falso(medias, serie="A", horizonte=5, n_episodios=10):
    """Tabela de resumo sintetica: medias na ordem dos buckets."""
    from estudos.positioning_zscore.buckets import ORDEM_BUCKETS
    return pd.DataFrame([
        {"serie": serie, "horizonte": horizonte, "bucket": b,
         "media": m, "n_obs": 50, "n_episodios": n_episodios,
         "ic_lo": m - 0.1, "ic_hi": m + 0.1}
        for b, m in zip(ORDEM_BUCKETS, medias)
    ])


def test_spread_contrarian_e_a_diferenca_das_pontas():
    r = _resumo_falso([2.0, 1.0, 0.0, -1.0, -3.0])
    assert spread_contrarian(r, "A", 5) == pytest.approx(2.0 - (-3.0))


def test_spread_contrarian_e_nan_se_falta_uma_ponta():
    r = _resumo_falso([2.0, 1.0, 0.0, -1.0, -3.0])
    r = r[r["bucket"] != "muito_long"]
    assert np.isnan(spread_contrarian(r, "A", 5))


def test_embaralhar_blocos_preserva_o_conteudo():
    v = np.arange(100, dtype=float)
    rng = np.random.default_rng(SEED)
    out = embaralhar_blocos(v, tamanho_bloco=10, rng=rng)
    assert out.size == v.size
    assert np.array_equal(np.sort(out), np.sort(v))


def test_embaralhar_blocos_mantem_vizinhanca_dentro_do_bloco():
    v = np.arange(100, dtype=float)
    rng = np.random.default_rng(SEED)
    out = embaralhar_blocos(v, tamanho_bloco=10, rng=rng)
    # Dentro de cada bloco de 10 a sequencia original sobrevive: a diferenca
    # entre vizinhos e 1 em pelo menos 9 de cada 10 posicoes.
    diffs = np.diff(out)
    assert np.count_nonzero(diffs == 1.0) >= 80


def test_embaralhar_blocos_realmente_muda_a_ordem():
    v = np.arange(100, dtype=float)
    rng = np.random.default_rng(SEED)
    out = embaralhar_blocos(v, tamanho_bloco=10, rng=rng)
    assert not np.array_equal(out, v)


def _painel_sem_sinal(n=500):
    idx = pd.date_range("2022-01-03", periods=n, freq="B")
    rng = np.random.default_rng(42)
    return pd.DataFrame({
        "Data": idx, "serie": "A",
        "nivel": rng.normal(0, 1, n).cumsum(),
        "z": rng.normal(0, 1.5, n),
        "r_5": rng.normal(0, 1, n),
    })


def test_placebo_nao_acha_sinal_onde_nao_ha():
    p = _painel_sem_sinal()
    out = placebo_blocos(p, "A", 5, reps=200)
    assert out["reps"] == 200
    assert 0.0 <= out["p_valor"] <= 1.0
    # Sem sinal por construcao: o p-valor nao deve ser minusculo.
    assert out["p_valor"] > 0.01


def test_placebo_acha_sinal_plantado():
    # z alto EMPURRA o retorno futuro para baixo, de proposito.
    n = 600
    idx = pd.date_range("2022-01-03", periods=n, freq="B")
    rng = np.random.default_rng(9)
    z = rng.normal(0, 1.5, n)
    p = pd.DataFrame({
        "Data": idx, "serie": "A", "nivel": z.cumsum(),
        "z": z, "r_5": -2.0 * z + rng.normal(0, 0.3, n),
    })
    out = placebo_blocos(p, "A", 5, reps=300)
    assert out["p_valor"] < 0.05
    assert out["observado"] > 0


def test_placebo_e_reprodutivel():
    p = _painel_sem_sinal()
    a = placebo_blocos(p, "A", 5, reps=100, seed=SEED)
    b = placebo_blocos(p, "A", 5, reps=100, seed=SEED)
    assert a == b


def test_espelho_detecta_curvas_invertidas():
    a = _resumo_falso([2.0, 1.0, 0.0, -1.0, -2.0], serie="A")
    b = _resumo_falso([-2.0, -1.0, 0.0, 1.0, 2.0], serie="B")
    esp = espelho_contabil(pd.concat([a, b], ignore_index=True), 5)
    linha = esp.iloc[0]
    assert set([linha["serie_a"], linha["serie_b"]]) == {"A", "B"}
    assert linha["correlacao"] == pytest.approx(-1.0)


def test_espelho_com_uma_serie_devolve_tabela_vazia():
    esp = espelho_contabil(_resumo_falso([1, 2, 3, 4, 5]), 5)
    assert esp.empty


def test_rotular_anedota_marca_bucket_com_poucos_episodios():
    r = _resumo_falso([1, 2, 3, 4, 5], n_episodios=3)
    out = rotular_anedota(r)
    assert out["anedota"].all()

    r2 = _resumo_falso([1, 2, 3, 4, 5], n_episodios=MIN_EPISODIOS)
    assert not rotular_anedota(r2)["anedota"].any()


def test_spearman_de_ordem_perfeita():
    assert spearman([1, 2, 3, 4, 5], [10, 20, 30, 40, 50]) == pytest.approx(1.0)
    assert spearman([1, 2, 3, 4, 5], [50, 40, 30, 20, 10]) == pytest.approx(-1.0)


def test_spearman_ignora_escala_e_usa_so_a_ordem():
    assert spearman([1, 2, 3], [1, 100, 10000]) == pytest.approx(1.0)


def test_veredito_negativo_quando_a_curva_nao_e_monotonica():
    r = rotular_anedota(_resumo_falso([1.0, -2.0, 0.5, 3.0, -1.0]))
    placebos = {("A", 5): {"p_valor": 0.001, "observado": 2.0,
                           "nulo_p05": -1.0, "nulo_p95": 1.0, "reps": 100}}
    ok, criterios = veredito(r, placebos)
    assert ok is False
    assert any(not c["passou"] for c in criterios)


def test_veredito_positivo_quando_tudo_passa():
    r = rotular_anedota(_resumo_falso([3.0, 1.5, 0.0, -1.5, -3.0]))
    placebos = {("A", 5): {"p_valor": 0.001, "observado": 6.0,
                           "nulo_p05": -1.0, "nulo_p95": 1.0, "reps": 100}}
    ok, criterios = veredito(r, placebos)
    assert ok is True
    assert all(c["passou"] for c in criterios)


def test_veredito_negativo_com_pontas_anedoticas():
    r = rotular_anedota(_resumo_falso([3.0, 1.5, 0.0, -1.5, -3.0],
                                      n_episodios=2))
    placebos = {("A", 5): {"p_valor": 0.001, "observado": 6.0,
                           "nulo_p05": -1.0, "nulo_p95": 1.0, "reps": 100}}
    ok, _ = veredito(r, placebos)
    assert ok is False
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `python -m pytest tests/positioning_zscore/test_falsificacao.py -v`
Expected: FAIL na coleta — `ModuleNotFoundError: No module named 'estudos.positioning_zscore.falsificacao'`.

- [ ] **Step 3: Implementar**

Criar `estudos/positioning_zscore/falsificacao.py`:

```python
"""As guardas do estudo. Rodam sempre e entram no relatorio sempre.

Principalmente quando o resultado principal e bonito: e ai que a tentacao de
nao rodar a falsificacao e maior.
"""
import numpy as np
import pandas as pd

from .buckets import ORDEM_BUCKETS, SEED, atribuir_bucket

# Abaixo disso, o bucket e anedota e nao sustenta conclusao. Com ~900
# observacoes e series persistentes, esse caso e provavel, nao hipotetico.
MIN_EPISODIOS = 5

# Bloco do placebo: 21 pregoes. Preserva a autocorrelacao do z (a posicao de
# amanha parece com a de hoje) e destroi o alinhamento com o retorno futuro.
BLOCO_PLACEBO = 21


def spread_contrarian(resumo: pd.DataFrame, serie: str, horizonte: int) -> float:
    """Efeito contrarian resumido num numero: ponta vendida menos ponta comprada.

    Sob a hipotese, `muito_short` (vendido em USD, esticado) e seguido de
    depreciacao do CLP (retorno positivo) e `muito_long` de apreciacao (retorno
    negativo). O spread e entao POSITIVO. Um numero, para o placebo ter o que
    comparar.
    """
    d = resumo[(resumo["serie"] == serie) & (resumo["horizonte"] == horizonte)]
    m = d.set_index("bucket")["media"]
    if "muito_short" not in m.index or "muito_long" not in m.index:
        return float("nan")
    return float(m["muito_short"] - m["muito_long"])


def embaralhar_blocos(v: np.ndarray, tamanho_bloco: int, rng) -> np.ndarray:
    """Permuta a serie em blocos contiguos, preservando o conteudo."""
    v = np.asarray(v)
    blocos = [v[i:i + tamanho_bloco] for i in range(0, v.size, tamanho_bloco)]
    ordem = rng.permutation(len(blocos))
    return np.concatenate([blocos[i] for i in ordem])


def _spread_de_uma_amostra(z: np.ndarray, r: np.ndarray) -> float:
    """Spread contrarian direto de dois vetores alinhados."""
    bucket = atribuir_bucket(pd.Series(z))
    valido = pd.notna(bucket) & pd.notna(r)
    if not valido.any():
        return float("nan")
    b = bucket[valido].to_numpy()
    rr = np.asarray(r)[valido.to_numpy()]

    curto = rr[b == "muito_short"]
    longo = rr[b == "muito_long"]
    if curto.size == 0 or longo.size == 0:
        return float("nan")
    return float(curto.mean() - longo.mean())


def placebo_blocos(
    painel: pd.DataFrame, serie: str, horizonte: int,
    reps: int = 1000, tamanho_bloco: int = BLOCO_PLACEBO, seed: int = SEED,
) -> dict:
    """Distribuicao nula do spread com o z embaralhado em blocos.

    O bootstrap da Task 4 responde "qual a incerteza da media deste bucket?".
    Esta rotina responde outra pergunta, mais dura: "que spread o acaso produz
    numa serie tao persistente quanto esta, sem nenhum alinhamento real com o
    retorno futuro?". Intervalo bonito com p-valor de placebo alto significa
    que o efeito e do formato da serie, nao de capacidade preditiva.

    O z entra com os NaN do burn-in incluidos, e eles se embaralham junto. Isso
    faz o numero de observacoes validas variar de permutacao para permutacao,
    o que acrescenta ruido a distribuicao nula sem enviesa-la — permutacao
    degenerada cai no filtro de `finitos`. Compactar a serie antes de
    embaralhar seria a alternativa; nao se fez porque ela quebraria os blocos
    de calendario, que sao justamente o que se quer preservar.
    """
    col = f"r_{horizonte}"
    d = painel[painel["serie"] == serie].sort_values("Data")
    z = d["z"].to_numpy(dtype=float)
    r = d[col].to_numpy(dtype=float)

    observado = _spread_de_uma_amostra(z, r)
    rng = np.random.default_rng(seed)

    nulos = np.empty(reps, dtype=float)
    for i in range(reps):
        nulos[i] = _spread_de_uma_amostra(
            embaralhar_blocos(z, tamanho_bloco, rng), r,
        )

    finitos = nulos[np.isfinite(nulos)]
    if not np.isfinite(observado) or finitos.size == 0:
        p = float("nan")
    else:
        # Bilateral: nao se assume o sinal do efeito antes de medi-lo.
        p = float((np.count_nonzero(np.abs(finitos) >= abs(observado)) + 1)
                  / (finitos.size + 1))

    return {
        "observado": observado,
        "p_valor": p,
        "nulo_p05": float(np.quantile(finitos, 0.05)) if finitos.size else float("nan"),
        "nulo_p95": float(np.quantile(finitos, 0.95)) if finitos.size else float("nan"),
        "reps": reps,
    }


def espelho_contabil(resumo: pd.DataFrame, horizonte: int) -> pd.DataFrame:
    """Correlacao entre as curvas dose-resposta de cada par de series.

    Os setores do mercado cambial somam ~zero: o que um compra, outro vendeu.
    Se a curva do Corporate e o negativo exato da curva do Offshore, o que se
    mediu foi essa identidade contabil, nao capacidade preditiva. Correlacao
    perto de -1 entre pares e o sinal de alerta.
    """
    d = resumo[resumo["horizonte"] == horizonte]
    curvas = d.pivot_table(index="bucket", columns="serie", values="media")
    curvas = curvas.reindex([b for b in ORDEM_BUCKETS if b in curvas.index])

    series = list(curvas.columns)
    linhas = []
    for i, a in enumerate(series):
        for b in series[i + 1:]:
            par = curvas[[a, b]].dropna()
            corr = (float(par[a].corr(par[b])) if len(par) >= 3
                    else float("nan"))
            linhas.append({"serie_a": a, "serie_b": b, "correlacao": corr})
    return pd.DataFrame(linhas, columns=["serie_a", "serie_b", "correlacao"])


def rotular_anedota(
    resumo: pd.DataFrame, min_episodios: int = MIN_EPISODIOS,
) -> pd.DataFrame:
    """Marca o bucket que tem poucos episodios independentes."""
    out = resumo.copy()
    out["anedota"] = out["n_episodios"] < min_episodios
    return out


def spearman(x, y) -> float:
    """Correlacao de ordem. Doze linhas de numpy em vez de uma dependencia.

    So a ORDEM importa aqui: a pergunta e se a curva dose-resposta desce
    monotonicamente, nao se desce em linha reta.
    """
    a = pd.Series(np.asarray(x, dtype=float)).rank()
    b = pd.Series(np.asarray(y, dtype=float)).rank()
    if a.std(ddof=0) == 0 or b.std(ddof=0) == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def veredito(
    resumo: pd.DataFrame, placebos: dict,
    min_episodios: int = MIN_EPISODIOS,
) -> tuple[bool, list[dict]]:
    """Quatro critérios por serie x horizonte. Passa quem passa em todos.

    O veredito global e positivo se ao menos uma combinacao serie x horizonte
    passar nos quatro. Se nenhuma passar, a conclusao do estudo e "nao ha
    evidencia" — que e uma conclusao, nao uma falha.

    `resumo` precisa vir de `rotular_anedota`.
    """
    if "anedota" not in resumo.columns:
        raise ValueError("resumo sem coluna 'anedota': passe por rotular_anedota")

    criterios = []
    for (serie, h), d in resumo.groupby(["serie", "horizonte"], sort=False):
        m = d.set_index("bucket")["media"]
        presentes = [b for b in ORDEM_BUCKETS if b in m.index]
        pl = placebos.get((serie, h), {})

        # 1. Curva desce de muito_short a muito_long.
        rho = spearman(range(len(presentes)), [m[b] for b in presentes])
        c_mono = np.isfinite(rho) and rho <= -0.9

        # 2. As duas pontas fora do intervalo do bucket neutro.
        neutro = d[d["bucket"] == "neutro"]
        c_pontas = False
        if not neutro.empty:
            lo = float(neutro["ic_lo"].iloc[0])
            hi = float(neutro["ic_hi"].iloc[0])
            pontas = d[d["bucket"].isin(["muito_short", "muito_long"])]
            c_pontas = len(pontas) == 2 and bool(
                ((pontas["media"] < lo) | (pontas["media"] > hi)).all()
            )

        # 3. Placebo rejeita o acaso.
        p = pl.get("p_valor", float("nan"))
        c_placebo = bool(np.isfinite(p) and p < 0.10)

        # 4. Nenhuma das pontas e anedota.
        pontas = d[d["bucket"].isin(["muito_short", "muito_long"])]
        c_episodios = len(pontas) == 2 and not bool(pontas["anedota"].any())

        criterios.append({
            "serie": serie, "horizonte": int(h),
            "rho": rho, "p_placebo": p,
            "monotonica": bool(c_mono), "pontas_fora": bool(c_pontas),
            "placebo": c_placebo, "episodios": bool(c_episodios),
            "passou": bool(c_mono and c_pontas and c_placebo and c_episodios),
        })

    return (any(c["passou"] for c in criterios), criterios)
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `python -m pytest tests/positioning_zscore/test_falsificacao.py -v`
Expected: todos passam.

Se `test_placebo_acha_sinal_plantado` falhar, verifique primeiro se o sinal plantado produz de fato buckets extremos povoados: `z ~ N(0, 1.5)` põe ~9% da massa fora de `|z| > 2`. Se o teste ficar instável, aumente `n` no teste, **não** afrouxe o limiar de p-valor.

- [ ] **Step 5: Commit**

```bash
git add estudos/positioning_zscore/falsificacao.py tests/positioning_zscore/test_falsificacao.py
git commit -m "Guardas do estudo: placebo, espelho contabil, anedota e veredito"
```

---

### Task 6: `relatorio.py` e `rodar.py`

**Files:**
- Create: `estudos/positioning_zscore/relatorio.py`, `estudos/positioning_zscore/rodar.py`
- Test: `tests/positioning_zscore/test_relatorio.py`

**Interfaces:**
- Consumes: tudo das Tasks 2-5
- Produces: `gerar(caminho: Path, resumo, espelhos: dict, placebos: dict, criterios: list, ok: bool, n_datas: int, inicio, fim) -> Path`; `python -m estudos.positioning_zscore.rodar` escrevendo `saida/positioning_zscore.html`

- [ ] **Step 1: Escrever o teste que falha**

Criar `tests/positioning_zscore/test_relatorio.py`:

```python
"""Smoke test do relatorio: escreve arquivo legivel com as secoes esperadas."""
import numpy as np
import pandas as pd

from estudos.positioning_zscore.buckets import ORDEM_BUCKETS
from estudos.positioning_zscore.falsificacao import (
    espelho_contabil, rotular_anedota, veredito,
)
from estudos.positioning_zscore.relatorio import gerar


def _resumo():
    linhas = []
    for serie in ("Offshore", "Corporate"):
        for h in (5, 21):
            for i, b in enumerate(ORDEM_BUCKETS):
                m = 2.0 - i
                linhas.append({
                    "serie": serie, "horizonte": h, "bucket": b,
                    "media": m, "n_obs": 40, "n_episodios": 6,
                    "ic_lo": m - 0.5, "ic_hi": m + 0.5,
                })
    return rotular_anedota(pd.DataFrame(linhas))


def test_gerar_escreve_html_com_as_secoes(tmp_path):
    r = _resumo()
    placebos = {
        (s, h): {"observado": 4.0, "p_valor": 0.02,
                 "nulo_p05": -1.0, "nulo_p95": 1.0, "reps": 100}
        for s in ("Offshore", "Corporate") for h in (5, 21)
    }
    espelhos = {h: espelho_contabil(r, h) for h in (5, 21)}
    ok, criterios = veredito(r, placebos)

    destino = tmp_path / "saida" / "estudo.html"
    caminho = gerar(destino, r, espelhos, placebos, criterios, ok,
                    n_datas=900, inicio=pd.Timestamp("2023-01-02"),
                    fim=pd.Timestamp("2026-08-31"))

    assert caminho.exists()
    html = caminho.read_text(encoding="utf-8")
    for esperado in ("Veredito", "dose-resposta", "Placebo",
                     "Espelho", "Offshore", "plotly"):
        assert esperado in html
    assert len(html) > 5000


def test_gerar_avisa_quando_nao_ha_evidencia(tmp_path):
    r = _resumo()
    r.loc[:, "media"] = 0.0                     # curva plana
    placebos = {
        (s, h): {"observado": 0.0, "p_valor": 0.80,
                 "nulo_p05": -1.0, "nulo_p95": 1.0, "reps": 100}
        for s in ("Offshore", "Corporate") for h in (5, 21)
    }
    espelhos = {h: espelho_contabil(r, h) for h in (5, 21)}
    ok, criterios = veredito(r, placebos)
    assert ok is False

    caminho = gerar(tmp_path / "e.html", r, espelhos, placebos, criterios,
                    ok, n_datas=900, inicio=pd.Timestamp("2023-01-02"),
                    fim=pd.Timestamp("2026-08-31"))
    assert "NEGATIVO" in caminho.read_text(encoding="utf-8")
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `python -m pytest tests/positioning_zscore/test_relatorio.py -v`
Expected: FAIL na coleta — `ModuleNotFoundError: No module named 'estudos.positioning_zscore.relatorio'`.

- [ ] **Step 3: Implementar `relatorio.py`**

Criar `estudos/positioning_zscore/relatorio.py`:

```python
"""Relatorio HTML do estudo, no tema do painel.

Este modulo NAO calcula nada. Se falta um numero aqui, ele vem calculado de
buckets.py ou falsificacao.py — nunca de uma conta feita no meio da formatacao.
"""
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from chart_builder import JGP_AZUL, JGP_PRETO, JGP_VERDE, JGP_VERMELHO  # noqa: E402

from .buckets import ORDEM_BUCKETS  # noqa: E402

ROTULO_BUCKET = {
    "muito_short": "z < -2<br>vendido esticado",
    "short": "-2 a -1<br>vendido",
    "neutro": "-1 a 1<br>neutro",
    "long": "1 a 2<br>comprado",
    "muito_long": "z > 2<br>comprado esticado",
}


def _fig_dose_resposta(resumo: pd.DataFrame, serie: str) -> str:
    """Curva dose-resposta de uma serie, uma linha por horizonte."""
    d = resumo[resumo["serie"] == serie]
    fig = go.Figure()
    cores = {5: JGP_VERDE, 21: JGP_AZUL, 63: JGP_PRETO}

    for h in sorted(d["horizonte"].unique()):
        dh = d[d["horizonte"] == h].set_index("bucket").reindex(
            [b for b in ORDEM_BUCKETS if b in set(d["bucket"])]
        ).dropna(subset=["media"])
        texto = [
            f"n={int(n)} · {int(e)} episodios" + (" · ANEDOTA" if a else "")
            for n, e, a in zip(dh["n_obs"], dh["n_episodios"], dh["anedota"])
        ]
        fig.add_trace(go.Scatter(
            x=[ROTULO_BUCKET.get(b, b) for b in dh.index],
            y=dh["media"], mode="lines+markers", name=f"{h} pregoes",
            line=dict(color=cores.get(h, JGP_VERMELHO), width=2),
            error_y=dict(
                type="data", symmetric=False,
                array=(dh["ic_hi"] - dh["media"]).clip(lower=0),
                arrayminus=(dh["media"] - dh["ic_lo"]).clip(lower=0),
                thickness=1, width=4,
            ),
            customdata=texto,
            hovertemplate="%{x}<br>media %{y:.2f} p.p.<br>%{customdata}<extra></extra>",
        ))

    fig.add_hline(y=0, line=dict(color=JGP_PRETO, width=1, dash="dot"))
    fig.update_layout(
        title=f"{serie}: retorno forward do USDCLP por faixa de z",
        template="jgp", height=380, margin=dict(l=60, r=20, t=64, b=80),
        yaxis_title="retorno medio (p.p.) · + = CLP depreciou",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=1, xanchor="right"),
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)


def _tabela(df: pd.DataFrame, colunas: dict, decimais: dict = None) -> str:
    """DataFrame -> table.data-table. `colunas` mapeia coluna -> cabecalho."""
    decimais = decimais or {}
    cab = "".join(f"<th>{t}</th>" for t in colunas.values())
    linhas = []
    for _, r in df.iterrows():
        celulas = []
        for c in colunas:
            v = r[c]
            if not isinstance(v, str) and pd.isna(v):
                celulas.append('<td class="num">&mdash;</td>')
            elif c in decimais and not isinstance(v, str):
                celulas.append(f'<td class="num">{v:.{decimais[c]}f}</td>')
            elif isinstance(v, (int,)) or (
                pd.api.types.is_number(v) and not isinstance(v, bool)
            ):
                celulas.append(f'<td class="num">{v:,.0f}</td>')
            else:
                celulas.append(f"<td>{v}</td>")
        linhas.append(f"<tr>{''.join(celulas)}</tr>")
    return (f'<table class="data-table"><thead><tr>{cab}</tr></thead>'
            f"<tbody>{''.join(linhas)}</tbody></table>")


def _tabela_criterios(criterios: list) -> str:
    d = pd.DataFrame(criterios)
    d = d.assign(
        serie_h=lambda x: x["serie"] + " · " + x["horizonte"].astype(str) + "d",
        mono=lambda x: x["monotonica"].map({True: "sim", False: "nao"}),
        pontas=lambda x: x["pontas_fora"].map({True: "sim", False: "nao"}),
        plac=lambda x: x["placebo"].map({True: "sim", False: "nao"}),
        epis=lambda x: x["episodios"].map({True: "sim", False: "nao"}),
        veredito=lambda x: x["passou"].map({True: "PASSOU", False: "reprovado"}),
    )
    return _tabela(
        d,
        {"serie_h": "Serie · horizonte", "rho": "rho de ordem",
         "mono": "curva desce", "pontas": "pontas fora do neutro",
         "p_placebo": "p do placebo", "plac": "placebo rejeita",
         "epis": "episodios suficientes", "veredito": "Veredito"},
        decimais={"rho": 2, "p_placebo": 3},
    )


def gerar(
    caminho: Path, resumo: pd.DataFrame, espelhos: dict, placebos: dict,
    criterios: list, ok: bool, n_datas: int, inicio, fim,
) -> Path:
    """Escreve o HTML. Nao decide nada: so mostra o que as outras pecas mediram."""
    titulo = ("RESULTADO POSITIVO: ao menos uma combinacao passou nas quatro guardas"
              if ok else
              "RESULTADO NEGATIVO: nenhuma combinacao passou nas quatro guardas")

    series = list(dict.fromkeys(resumo["serie"]))
    graficos = "".join(
        f'<div class="card">{_fig_dose_resposta(resumo, s)}</div>' for s in series
    )

    tab_resumo = _tabela(
        resumo.assign(
            rotulo=lambda x: x["anedota"].map({True: "anedota", False: ""}),
        ).sort_values(["serie", "horizonte"]),
        {"serie": "Serie", "horizonte": "Horizonte", "bucket": "Bucket",
         "media": "Retorno medio (p.p.)", "ic_lo": "IC 5%", "ic_hi": "IC 95%",
         "n_obs": "n", "n_episodios": "Episodios", "rotulo": "Alerta"},
        decimais={"media": 2, "ic_lo": 2, "ic_hi": 2},
    )

    tab_placebo = _tabela(
        pd.DataFrame([
            {"serie_h": f"{s} · {h}d", "observado": v["observado"],
             "p_valor": v["p_valor"], "nulo_p05": v["nulo_p05"],
             "nulo_p95": v["nulo_p95"], "reps": v["reps"]}
            for (s, h), v in placebos.items()
        ]),
        {"serie_h": "Serie · horizonte", "observado": "Spread observado",
         "p_valor": "p bilateral", "nulo_p05": "nulo 5%",
         "nulo_p95": "nulo 95%", "reps": "Repeticoes"},
        decimais={"observado": 2, "p_valor": 3, "nulo_p05": 2, "nulo_p95": 2},
    )

    tab_espelho = "".join(
        f"<p class='sub'>Horizonte de {h} pregoes</p>"
        f"<div class='card'>{_tabela(e, {'serie_a': 'Serie A', 'serie_b': 'Serie B', 'correlacao': 'Correlacao das curvas'}, decimais={'correlacao': 2})}</div>"
        for h, e in sorted(espelhos.items()) if not e.empty
    )

    corpo = f"""
<h2>Veredito</h2>
<p class="lead"><b>{titulo}</b></p>
<p class="sub">Amostra de {n_datas:,} pregoes com z definido, de
{pd.Timestamp(inicio):%d/%m/%Y} a {pd.Timestamp(fim):%d/%m/%Y}. Z-score de janela
rolante de 252 pregoes, calculado point-in-time. Convencao de sinal: acima de
zero = comprando USD. Retorno forward positivo = CLP depreciou.</p>
<div class="card">{_tabela_criterios(criterios)}</div>
<p class="sub">As quatro guardas, todas exigidas: a curva desce monotonicamente
de vendido-esticado a comprado-esticado (rho de ordem &le; -0,9); as duas pontas
caem fora do intervalo de confianca do bucket neutro; o placebo por
embaralhamento em blocos rejeita o acaso (p &lt; 0,10); e nenhuma das pontas e
anedota (menos de 5 episodios independentes).</p>

<h2>Curva dose-resposta</h2>
<p class="sub">Retorno medio do USDCLP nos 5, 21 e 63 pregoes seguintes, por faixa
de z. Barras de erro sao o intervalo de 90% por block bootstrap circular, com
bloco do tamanho do horizonte — os retornos se sobrepoem, e um intervalo i.i.d.
seria estreito demais por um fator grande.</p>
{graficos}

<h2>Tabela completa</h2>
<div class="card">{tab_resumo}</div>
<p class="sub">Episodios sao blocos contiguos de dias no bucket, nao dias: 40 dias
seguidos com a posicao esticada sao UM episodio. Bucket com menos de 5 episodios
recebe o alerta de anedota e nao sustenta conclusao, qualquer que seja o retorno
medio.</p>

<h2>Placebo por embaralhamento em blocos</h2>
<p class="sub">O z e permutado em blocos de 21 pregoes, preservando sua
persistencia e destruindo o alinhamento com o retorno futuro. O p-valor e a
fracao de permutacoes que produziu spread tao extremo quanto o observado.
Intervalo de confianca bonito com p-valor alto significa efeito do formato da
serie, nao capacidade preditiva.</p>
<div class="card">{tab_placebo}</div>

<h2>Espelho contabil</h2>
<p class="sub">Os setores do mercado cambial somam aproximadamente zero: o que um
setor compra, outro vendeu. Correlacao perto de -1 entre as curvas de duas series
indica que o que se mediu foi essa identidade, nao capacidade preditiva.</p>
{tab_espelho or "<p class='sub'>Serie unica: sem par para comparar.</p>"}
"""

    html = f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<title>Niveis esticados de positioning como sinal contrarian</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<script src="https://cdn.plot.ly/plotly-2.35.0.min.js"></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<style>
:root{{--bg:#F6F4EE;--card:#fff;--ink:#0A0A0A;--ink2:#4A4A48;--ink3:#8C8C88;
--verde:#00B050;--rule:#DDD9CE;--faint:#ECE8DC;--line:#DDD9CE;
--green:#00B050;--green-dark:#008A3F}}
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
.card{{background:var(--card);border:1px solid var(--faint);padding:.75rem .9rem;margin-bottom:14px;overflow-x:auto}}
table.data-table{{border-collapse:collapse;font-size:12px;width:100%}}
table.data-table th,table.data-table td{{border:1px solid var(--line);padding:5px 10px}}
table.data-table thead th{{background:var(--green);color:#fff;font-weight:700;border-color:var(--green-dark)}}
table.data-table td.num{{text-align:right;font-variant-numeric:tabular-nums}}
.meta{{font-size:.72rem;text-transform:uppercase;letter-spacing:.1em;color:var(--ink3);margin-bottom:2rem}}
</style></head><body>
<h1>Niveis esticados de positioning como sinal contrarian</h1>
<div class="meta">JGP Emerging Markets &middot; Chile &middot; gerado em {pd.Timestamp.now():%d/%m/%Y %H:%M}</div>
{corpo}
</body></html>"""

    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(html, encoding="utf-8")
    return caminho
```

- [ ] **Step 4: Rodar e confirmar que o teste do relatório passa**

Run: `python -m pytest tests/positioning_zscore/test_relatorio.py -v`
Expected: 2 passed.

- [ ] **Step 5: Implementar `rodar.py`**

Criar `estudos/positioning_zscore/rodar.py`:

```python
"""Entrypoint do estudo. Encadeia dados -> buckets -> falsificacao -> relatorio.

    python -m estudos.positioning_zscore.rodar
    python -m estudos.positioning_zscore.rodar --reps 1000 --reps-placebo 300

As repeticoes menores servem para iterar rapido; o numero do relatorio final e
o padrao (5.000 do bootstrap, 1.000 do placebo).
"""
import argparse
import logging
from pathlib import Path

from .buckets import SEED, resumir
from .dados import HORIZONTES, montar_painel
from .falsificacao import (
    espelho_contabil, placebo_blocos, rotular_anedota, veredito,
)
from .relatorio import gerar

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SAIDA = Path(__file__).resolve().parent / "saida" / "positioning_zscore.html"


def _parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reps", type=int, default=5000,
                   help="repeticoes do block bootstrap (padrao: 5000)")
    p.add_argument("--reps-placebo", type=int, default=1000,
                   help="repeticoes do placebo (padrao: 1000)")
    p.add_argument("--saida", type=Path, default=SAIDA,
                   help=f"destino do HTML (padrao: {SAIDA})")
    return p.parse_args(argv)


def main(argv=None) -> Path:
    args = _parse_args(argv)

    painel = montar_painel()
    com_z = painel[painel["z"].notna()]
    logger.info(
        "Painel: %d linhas, %d series, z definido em %d datas (%s a %s)",
        len(painel), painel["serie"].nunique(),
        com_z["Data"].nunique(),
        com_z["Data"].min().date(), com_z["Data"].max().date(),
    )

    logger.info("Resumindo por bucket (bootstrap com %d repeticoes)...", args.reps)
    resumo = rotular_anedota(resumir(painel, horizontes=HORIZONTES,
                                     reps=args.reps, seed=SEED))

    logger.info("Placebo (%d repeticoes por combinacao)...", args.reps_placebo)
    placebos = {}
    for serie in painel["serie"].unique():
        for h in HORIZONTES:
            placebos[(serie, h)] = placebo_blocos(
                painel, serie, h, reps=args.reps_placebo, seed=SEED,
            )

    espelhos = {h: espelho_contabil(resumo, h) for h in HORIZONTES}
    ok, criterios = veredito(resumo, placebos)

    caminho = gerar(
        args.saida, resumo, espelhos, placebos, criterios, ok,
        n_datas=com_z["Data"].nunique(),
        inicio=com_z["Data"].min(), fim=com_z["Data"].max(),
    )
    logger.info("Veredito: %s", "POSITIVO" if ok else "NEGATIVO")
    for c in criterios:
        if c["passou"]:
            logger.info("  passou: %s %dd (rho=%.2f, p=%.3f)",
                        c["serie"], c["horizonte"], c["rho"], c["p_placebo"])
    logger.info("Relatorio em %s", caminho)
    return caminho


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Rodar a suíte inteira**

Run: `python -m pytest`
Expected: todos os testes passam (Tasks 1-6).

- [ ] **Step 7: Commit**

```bash
git add estudos/positioning_zscore/relatorio.py estudos/positioning_zscore/rodar.py tests/positioning_zscore/test_relatorio.py
git commit -m "Relatorio HTML e entrypoint do estudo de z-score contrarian"
```

---

### Task 7: Rodar com dado real e registrar o achado

**Files:**
- Create: `estudos/positioning_zscore/README.md`
- Modify: `.gitignore` (ignorar `estudos/*/saida/`)

**Interfaces:**
- Consumes: `rodar.main` da Task 6
- Produces: o resultado empírico do estudo, escrito por extenso

- [ ] **Step 1: Rodar rápido primeiro, para pegar erro de integração**

Run: `python -m estudos.positioning_zscore.rodar --reps 200 --reps-placebo 100`
Expected: log com o painel carregado (~1.150 datas, 5 séries), o veredito, e o caminho do HTML. Leva alguns minutos, quase todos em rede.

Se estourar erro de coluna ausente, confira os nomes em `SERIES` contra `config.SERIES_NAMES_ALL` — são eles que o BCCh devolve.

- [ ] **Step 2: Rodar de verdade**

Run: `python -m estudos.positioning_zscore.rodar`
Expected: mesmo fluxo, com 5.000 repetições de bootstrap e 1.000 de placebo. Anote o veredito e, para cada série × horizonte, o rho de ordem e o p-valor do placebo.

- [ ] **Step 3: Abrir o HTML e ler o resultado**

Run: `start estudos/positioning_zscore/saida/positioning_zscore.html`

Leia de fato, não só confira que abriu. Perguntas a responder: a curva desce? As pontas têm episódios suficientes ou quase tudo virou anedota? O espelho contábil mostra correlação perto de -1 entre setores — e se mostra, o "achado" é identidade contábil?

- [ ] **Step 4: Ignorar a saída no git**

Adicionar ao fim de `.gitignore`:

```
estudos/*/saida/
```

O HTML é regenerável a partir do código e muda a cada execução (tem timestamp). Versioná-lo só produz diff de ruído.

- [ ] **Step 5: Escrever o README com o achado**

Criar `estudos/positioning_zscore/README.md`. Estrutura obrigatória, preenchida com os **números reais** da execução do Step 2 — não com os do exemplo:

```markdown
# Niveis esticados de positioning como sinal contrarian

## O que se testou

Se um nivel esticado de positioning cambial chileno, medido por z-score rolante
de 252 pregoes point-in-time, antecipa reversao do USDCLP nos 5, 21 e 63 pregoes
seguintes.

Series: Fundos de Pensao, Offshore, Corporate, Bancos e o agregado
Pensoes + Offshore, todas em convencao compra-de-USD.

## Como rodar

    python -m estudos.positioning_zscore.rodar

Saida em `saida/positioning_zscore.html` (nao versionada).

## Resultado

[VEREDITO, com os numeros: rho de ordem e p-valor do placebo por serie e
horizonte. Se nenhuma combinacao passou, diga isso de forma direta — "nao ha
evidencia de sinal contrarian nesta amostra" e a conclusao, nao a ausencia dela.]

## O que limita a conclusao

A amostra do BCCh comeca em 2022-01-03 e nao ha como alonga-la: pedir data
inicial anterior nao traz dado. Com o burn-in de 252 pregoes do z-score, sobram
[N] pregoes com z definido. Os buckets extremos contem [N] episodios
independentes — [suficientes / poucos demais para sustentar conclusao].

Retornos forward se sobrepoem (com h=63, observacoes vizinhas compartilham 62
dos 63 dias), o que motiva o block bootstrap; e os setores somam ~zero por
identidade contabil, o que motiva o teste de espelho.

## Fora de escopo

- Z-score do fluxo (variacao da posicao) em vez do nivel.
- Controlar por DXY, cobre ou diferencial de juros.
- Varrer a janela do z-score em busca da que funciona. Deliberado: o desenho
  inteiro existe para evitar escolha de parametro depois de ver resultado.
```

- [ ] **Step 6: Rodar a suíte uma última vez**

Run: `python -m pytest`
Expected: todos passam.

- [ ] **Step 7: Commit**

```bash
git add estudos/positioning_zscore/README.md .gitignore
git commit -m "Estudo de z-score contrarian: resultado com dado real"
```

---

## Cobertura do spec

| Requisito do spec | Task |
|---|---|
| Séries em convenção compra-de-USD, 4 setores + agregado | 2 |
| Amostra 2022-01-03 em diante, ~900 obs úteis | 2 (burn-in), 7 (registro) |
| Z-score rolante 252, point-in-time, em `src/data_processor.py` | 1 |
| Bordas: burn-in de span cheio, `min_obs=200`, desvio degenerado | 1 |
| Retorno forward log ×100, h ∈ {5, 21, 63}, NaN na cauda | 2 |
| Buckets fixos, exaustivos e exclusivos | 3 |
| Média, n, episódios independentes, IC 90% por bucket | 3, 4 |
| Block bootstrap circular, bloco = h, 5.000 reps, semente fixa | 4 |
| Guarda 1: espelho contábil | 5 |
| Guarda 2: placebo por embaralhamento em blocos | 5 |
| Guarda 3: rótulo de anedota abaixo de 5 episódios | 5 |
| Guarda 4: teste de vazamento | 1 |
| `relatorio.py` não calcula nada | 5 (veredito), 6 (relatório) |
| Estrutura de arquivos e testes espelhados | 0, 1-6 |
| Nenhuma dependência nova | todas (Spearman e bootstrap em numpy) |
