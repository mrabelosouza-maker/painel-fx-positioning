# Fluxo spot dos fundos de pensao no painel de positioning

Data: 2026-08-27

## Problema

O painel hoje mostra a posicao dos fundos de pensao chilenos **so pela perna de
NDF** (saldo forward que o BCCh publica para o setor 42). Falta a perna spot: o
dolar que os AFPs efetivamente compram para mandar dinheiro para fora.

## Intuicao a capturar

Os afiliados escolhem entre cinco fundos, A (mais arriscado) a E (menos
arriscado). Cada tipo de fundo tem um perfil de alocacao proprio, e a fatia
offshore cai monotonicamente do A para o E:

| Fundo | % offshore total | % renda variavel offshore |
|-------|------------------|---------------------------|
| A     | 83,6%            | 67,2%                     |
| B     | 69,3%            | 48,8%                     |
| C     | 53,0%            | 30,7%                     |
| D     | 30,3%            | 14,2%                     |
| E     | 12,6%            |  4,2%                     |

(posicao de jul/2026)

Logo: quando o fluxo diario de dinheiro se concentra nos fundos mais
arriscados, uma fatia maior desse dinheiro vira compra de dolar. O fluxo por
tipo de fundo, ponderado pela fatia offshore de cada fundo, e uma proxy da
demanda de USD spot dos AFPs.

## Fontes de dados

### 1. Fluxo diario por tipo de fundo (dados alternativos)

`DadosDiarios.xlsx`, abas `Fundo A` ... `Fundo E`. Cada aba tem, para as seis
AFPs (Habitat, Cuprum, Modelo, Capital, Provida, Planvital), duas colunas
vindas da Bloomberg:

- valor cuota (campo `PR005`), colunas E, G, I, K, M, O
- patrimonio do fundo (campo `FD004`, MM CLP), colunas F, H, J, L, N, P

Data na coluna D, dados a partir da linha 9.

O fluxo (dinheiro novo, limpo de retorno) de cada AFP `k` no dia `t`:

    fluxo_k,t = q_k,t-1 * NAV_k,t / q_k,t - NAV_k,t-1

e o fluxo do tipo de fundo e a soma sobre as seis AFPs. Unidade: MM CLP.

**Nao usar a aba `Consolidado`.** Ela tem exatamente essa conta em formulas de
Excel, mas o range e fixo e para dois dias antes das abas por fundo. Recomputar
em Python reproduz o `Consolidado` com diferenca maxima 0,0 em todas as cinco
colunas e ganha dois dias de frescor.

Dias em que os cinco fundos dao **exatamente zero** sao Bloomberg estagnado
(cuota e patrimonio nao atualizaram), nao ausencia de fluxo. Tratar como
faltante, nao como zero.

### 2. Fatia offshore por tipo de fundo

`Fundos de Pensao.xlsx`, abas `Fundo A` ... `Fundo E`, bloco `% Portfolio`,
coluna `Total Offshore` (coluna M). Mensal, ultimo ponto jul/2026 (a
Superintendencia publica com cerca de 1,5 mes de defasagem). Reindexar para
diario com forward-fill.

Fica registrado que a fatia de **renda variavel offshore** (coluna N) tem
correlacao 0,996 com a de offshore total: a forma da serie e a mesma, so a
escala muda (cerca de 20% menor). Usamos offshore total, que casa melhor o
nivel do fluxo observado.

### 3. Series do BCCh

- NDF setor 42 (ja no painel): `F099.DER.STO.Z.40.R.42.NET.Z.MMUSD.MLME.Z.Z.0.D`
  Nivel, otica do banco residente. Nivel atual +33,2 bn = AFPs net **short** USD.
- Spot setor 42 (nova): `F099.SPT.FLU.Z.40.R.42.NET.Z.MMUSD.MLME.Z.Z.0.D`
  Fluxo diario, otica do banco residente, 1050 obs desde jun/2022.
- USDCLP fechamento: `fetch_usdclp_closing()`, que ja existe.

## Construcao

Proxy de demanda de USD spot, em MM USD:

    spot_proxy_t = SOMA_j [ (F_j,t / USDCLP_t) * w_off_j,t ]

Decomposicao, com `w_barra` = media das fatias offshore ponderada pelo AUM de
cada fundo:

    dinheiro_novo_t = (SOMA_j F_j,t / USDCLP_t) * w_barra_t
    switch_t        = SOMA_j [ (F_j,t / USDCLP_t) * (w_off_j,t - w_barra_t) ]
    spot_proxy_t    = dinheiro_novo_t + switch_t

`dinheiro_novo` e o efeito da contribuicao liquida entrando no sistema;
`switch` e o efeito puro de realocacao entre tipos de fundo, que e o que a
intuicao do painel quer isolar.

## Convencao de sinal

**Em todos os paineis da aba: acima de zero = compra de CLP, abaixo de zero =
venda de CLP.** Unidade MM USD.

| Perna | Serie crua | Convertida para compra-de-CLP |
|-------|-----------|-------------------------------|
| NDF | nivel BCCh (positivo = AFP short USD) | `+ delta_7d(nivel)` |
| Spot observado | fluxo BCCh, otica do banco (positivo = banco compra USD do AFP) | `+ valor` |
| Spot proxy | `spot_proxy_t` = demanda de USD | `- spot_proxy_t` |

O `delta_7d` do NDF usa a mesma convencao de dias corridos da funcao
`compute_deltas` que o painel ja usa nas outras abas: para cada data busca o
dia util mais proximo com data menor ou igual a t - 7 dias.

## Validacao ja executada

Proxy contra o fluxo spot observado do BCCh, jun/2022 a ago/2026 (1049 dias):

- correlacao diaria 0,17; semanal 0,35; mensal 0,22. Sinal correto em todas.
- nivel medio: proxy 10,7 MM USD/dia de demanda de USD, observado 21,3. O proxy
  captura cerca de metade do fluxo executado.
- proxy com peso offshore total vs peso renda variavel offshore: correlacao
  0,996 entre si.

Interpretacao: o proxy carrega sinal real mas incompleto, e por isso entra no
painel **ao lado** do observado, nunca no lugar dele. Ele adiciona o angulo que
o observado nao tem, a composicao do fluxo por tipo de fundo.

## Output: aba `FLUXO AFP: NDF + SPOT`

1. **Painel principal.** Tres barras, cada uma o acumulado dos ultimos 7 dias
   corridos: NDF, spot proxy, spot observado. Ancorar a janela na ultima data
   em que as tres pernas existem, porque as fontes tem defasagem diferente
   (BCCh 25/ago, proxy 24/ago na data deste spec). Imprimir a janela no titulo.
2. **Historico semanal.** Barras agrupadas por semana (W-FRI) das tres pernas,
   abrindo nas ultimas 12 semanas, no padrao de `make_weekly_legs_bars`.
3. **Decomposicao do proxy.** Barras empilhadas semanais: dinheiro novo e
   switch, com marcador do total.
4. **Tabela.** Ultimos 5 dias x tres pernas + net + % USDCLP. Uma linha de
   rodape com a ultima data de cada fonte, para o lag ficar explicito.

## Robustez do build

Os dois `.xlsx` vivem no R: e o `.gitignore` do repo exclui `*.xlsx`. O build
local roda diario pelo `update_dashboard.bat` e ve o R:, mas o GitHub Actions
das 12:00 UTC nao ve.

Solucao: quando o build le os xlsx com sucesso, grava
`data/afp_flow_daily.csv` (data, fluxo A-E em MM CLP, fatia offshore A-E, AUM
A-E) e esse CSV e commitado junto com o `docs/index.html`. Quando os xlsx nao
estao acessiveis, o build le o CSV e a aba mostra a data do ultimo dado
disponivel. Se nem o CSV existir, a aba renderiza uma mensagem de
indisponibilidade e o resto do painel segue normal.

## Arquivos

| Arquivo | Mudanca |
|---------|---------|
| `src/config.py` | serie spot setor 42, caminhos dos xlsx, caminho do CSV de cache, lista de fundos |
| `src/data_fetcher.py` | `fetch_afp_daily_flows()`, `fetch_afp_offshore_weights()`, cache CSV |
| `src/data_processor.py` | `build_afp_spot_flow()`, `build_afp_weekly_legs()`, `build_afp_7d_summary()` |
| `src/chart_builder.py` | `make_afp_7d_bars()`, `make_afp_weekly_bars()`, `make_afp_decomp_bars()` |
| `src/table_builder.py` | `make_afp_legs_table()` |
| `src/build.py` | `build_afp_flow_section()` |
| `templates/dashboard.html` | aba nova |
| `.github/workflows/build.yml` | `git add data/afp_flow_daily.csv` |
| `update_dashboard.bat` | `git add data\afp_flow_daily.csv` |

## Fora de escopo

- Reescrever a aba `Fluxo spot` mensal do `Fundos de Pensao.xlsx`, que usa outra
  metodologia (variacao de AUM onshore vs offshore). Fica como esta.
- Calibrar o proxy para casar o nivel do observado (regressao, fator de escala).
  O painel mostra as duas series cruas e o leitor compara.
- Buscar cuota e patrimonio das AFPs direto de alguma API. Verificado que os
  tickers `AFP*` nao existem na tabela `ODS.MACRO_BBG` do Oracle, entao a
  dependencia do Excel local e inevitavel nesta versao.
