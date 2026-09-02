# Fluxo AFP previsto a partir de bolsa global — desenho

Data: 2026-09-02
Status: aprovado, pronto para plano de implementação

## Hipótese

O rebalanceamento cambial dos fundos de pensão chilenos é mecânico. O AFP mantém
uma carteira externa de valor `A` (em USD) e hedgeia uma fração `h` dela contra o
CLP. Quando a bolsa global sobe `r%`, a carteira externa vale `A(1+r)` e, para
manter a razão de hedge, o AFP precisa **vender `h·A·r` de USD a termo**. O ajuste
não é instantâneo: vem com defasagem de dias.

Se isso for verdade, o retorno de bolsa global — observável em tempo real —
antecipa o fluxo cambial do AFP, que o BCCh só publica com defasagem.

O valor para operar não é saber o que o BCCh vai imprimir. É que esse hedge é
**venda de dólar de verdade batendo no mercado**: se a bolsa global subiu 3% na
semana, a oferta de USD dos próximos dias já está determinada, e a publicação do
BCCh é apenas a confirmação posterior.

## Escopo

**Dentro.** Um módulo de pesquisa que mede se a relação existe e quão forte é.
Roda offline e produz um relatório HTML.

**Fora.** Qualquer alteração no painel FX Positioning. Nenhuma aba nova, nenhuma
mudança em `src/`. O estudo consome o painel como biblioteca, não o modifica.

**Fora, adiado para a fase 2.** A pergunta "o fluxo previsto antecipa o USDCLP?".
Só faz sentido depois que a fase 1 responder. Registrada no fim deste documento
para não se perder.

## Dados

Tudo já disponível: BCCh via `data_fetcher.fetch_bcentral_matrix`, Bloomberg via
`data_fetcher.fetch_bbg_closing` (Oracle `ODS.MACRO_BBG`). Nenhuma fonte nova,
nenhum passo manual, nenhuma planilha.

### Alvo

De `data_processor.build_afp_spot_flow(dados)`, já na convenção de compra-de-USD
(acima de zero = compra de USD):

| Coluna | O que é | Papel |
|---|---|---|
| `ndf_1d` | Variação diária do saldo de NDF do setor 42 | A perna de hedge — alvo principal |
| `net_1d` | `ndf_1d + spot_bcch` | O fluxo cambial total do setor — alvo secundário |

Os dois são modelados **separadamente**, de propósito. Se a bolsa dirige o NDF mas
não o spot, isso é evidência a favor do mecanismo de hedge mecânico, não um
detalhe de implementação: o hedge se faz a termo, não à vista.

### Preditores

| Ticker | Série | Papel |
|---|---|---|
| `MXWO Index` | MSCI World | Preditor principal |
| `MXWD Index` | MSCI ACWI | Alternativa (cobertura mais ampla) |
| `SPX Index` | S&P 500 | Alternativa (proxy mais líquida) |
| `MXEF Index` | MSCI EM | Controle — a carteira externa do AFP não é só DM |

Retorno logarítmico diário, em USD (a carteira e o hedge são em USD).

### Amostra

2022-06-01 a 2026-08-31, 1.054 observações. **Fixa: é o limite do dado do BCCh,
não uma escolha de configuração.** Não há histórico anterior a buscar, e o
`BCENTRAL_FIRSTDATE = "2022-06-01"` do `config.py` já reflete esse limite.

A amostra é modesta e não vai crescer, o que torna a busca por especificação o
principal risco metodológico deste estudo. Ver o critério de plateau na seção de
critério de sucesso.

### Alinhamento

Interseção de dias úteis, sem `ffill` silencioso: uma observação só entra se o
alvo e o preditor existirem naquele dia. Feriado chileno com bolsa global aberta
não vira zero de fluxo, vira ausência.

## Arquitetura

Pasta nova `estudos/afp_leading/`, fora de `src/`. Quatro módulos, cada um com uma
responsabilidade e testável sozinho.

```
estudos/afp_leading/
├── dados.py       # monta o painel diário alinhado
├── modelo.py      # estrutura de defasagem e estimação de beta
├── avaliacao.py   # metricas fora de amostra e estabilidade
└── relatorio.py   # HTML padrao JGP
```

### `dados.py`

`montar_painel(inicio, fim) -> pd.DataFrame`

Uma linha por dia útil, colunas: `Data`, `ndf_1d`, `spot_bcch`, `net_1d`,
`r_mxwo`, `r_mxwd`, `r_spx`, `r_mxef`. Sem NaN nas colunas usadas — a filtragem
acontece aqui, uma vez, para que os módulos seguintes não precisem se preocupar.

Depende de `src/data_fetcher.py` e `src/data_processor.py` do painel. Não os
modifica.

### `modelo.py`

`estrutura_defasagem(painel, alvo, preditor) -> pd.DataFrame`

Varre duas famílias de especificação e devolve uma linha por especificação com o
coeficiente, o erro-padrão Newey-West, o t-stat e o R² dentro de amostra:

- **Defasagem pontual:** `fluxo(t) ~ a + b·r(t-k)`, para `k = 0..10`
- **Janela acumulada:** `fluxo(t) ~ a + b·R(t-w..t-1)`, onde `R` é o retorno
  acumulado, para `w = 1..21`

`k = 0` é reportado mas **marcado como não utilizável**: o MXWO fecha depois do
mercado chileno, então o retorno do mesmo dia não estaria disponível a tempo. Ele
entra só como referência de quanto do fluxo é contemporâneo.

Erros-padrão Newey-West com defasagem `w` nas janelas acumuladas — elas se
sobrepõem e os resíduos são autocorrelacionados por construção.

Uma **especificação** (`spec`, usada também no `avaliacao.py`) é a tripla
`(alvo, preditor, defasagem)`, onde defasagem é `("pontual", k)` ou
`("acumulada", w)`. É o identificador de uma linha da tabela acima.

`beta_movel(painel, spec) -> pd.DataFrame`

β estimado em janela expansível e em janela móvel de 252 dias, sempre usando só
dado até `t-1`. É esse β que a fase 2 usaria; e a estabilidade dele é parte do
critério de sucesso.

### `avaliacao.py`

`avaliar(painel, spec) -> dict`

- **R² fora de amostra**, `1 - SSE_modelo/SSE_referencia`, referência = média
  expansível do próprio fluxo. Previsão em `t` usa coeficientes ajustados só até
  `t-1`.
- **Correlação** entre previsto e realizado, e **erro absoluto médio em USD mm** —
  o R² diz se há relação, o erro em USD mm diz se ela é grande o bastante para
  significar alguma coisa numa mesa.
- **Split de amostra** em duas metades: coeficiente, t-stat e R² em cada.

### `relatorio.py`

HTML no padrão JGP, usando o skill `jgp-html-report` e o mesmo tema Plotly
(`template="jgp"`) do painel. Quatro seções: estrutura de defasagem, β ao longo do
tempo, previsto vs realizado, e a tabela de decisão contra o critério de sucesso.

## Portão de sanidade

Fica no `modelo.py` e roda antes de qualquer avaliação, para não gastar as outras
peças com um mecanismo que não existe.

**β̂ tem que ser negativo.** Bolsa global sobe → a carteira externa vale mais → o
AFP precisa vender mais USD a termo → fluxo negativo na convenção de compra-de-USD.
β̂ positivo significa que a hipótese está errada, não que o modelo precisa de
ajuste.

**A magnitude implícita tem que ser plausível.** Com o fluxo em USD mm e `r`
fracionário, `β = -h·A`, então β̂ = -300 significa que 1% de bolsa move USD 3 mm de
hedge, e uma exposição hedgeada implícita de USD 300 mm. A exposição externa do AFP
é da ordem de dezenas de bilhões de USD e a razão de hedge historicamente fica
numa faixa larga, então `h·A` entre **USD 5 bi e 90 bi** passa; fora disso, para.

Esta é uma checagem de ordem de grandeza, não de precisão. Se `h·A` cair perto de
qualquer uma das bordas, o número deve ser confrontado com o ativo externo
publicado pela Superintendencia de Pensiones antes de seguir — dado que hoje não
está no repositório e que seria a próxima aquisição, se necessária.

## Critério de sucesso

Fixado aqui, antes de rodar, para que o resultado não seja escolhido depois.

O estudo é considerado **positivo** se as três condições valerem:

1. β̂ negativo, com `h·A` implícito dentro da faixa do portão de sanidade
2. R² fora de amostra > 0,10 em pelo menos uma especificação de defasagem
   utilizável (`k ≥ 1` ou janela acumulada)
3. Nas duas metades da amostra: β̂ com o mesmo sinal nas duas, e a razão entre o
   maior e o menor em módulo dentro de 2x
4. **Plateau:** a especificação vencedora não pode ser um pico isolado. Os
   vizinhos imediatos na grade (`k±1`, ou `w±1`) precisam ter β̂ do mesmo sinal e
   pelo menos metade do R² fora de amostra do vencedor

O critério 4 é a defesa contra a busca. Com 1.054 observações fixas e ~32
especificações varridas, o vencedor da grade tem probabilidade alta de ser sorte.
Mas um mecanismo de rebalanceamento real produz estrutura de defasagem **suave**:
se o AFP ajusta o hedge ao longo de alguns dias, `k=3` funcionar implica `k=2` e
`k=4` funcionarem também. Um vencedor isolado, cercado de vizinhos mortos, é a
assinatura de ruído, não de mecanismo — e é exatamente o que a busca produz.

Esta é uma checagem barata que a amostra sustenta, ao contrário de holdout puro
(que gastaria observações que não temos) ou de correção de Bonferroni (que, com
32 testes e uma amostra desse tamanho, mataria também um efeito verdadeiro).

Falhar qualquer uma delas é resultado **negativo**, e o resultado negativo é
entregável: o relatório sai com o β̂ e os R² medidos, para que a hipótese não
precise ser revisitada do zero.

Não há terceira via. "Deu quase" não conta.

## Limitações declaradas

Vão no relatório, não só neste documento.

- **1.054 observações, e não há mais.** É o limite do dado do BCCh. Pouco para
  corte de regime; o split em duas metades é o máximo que a amostra sustenta, e
  cada metade cobre ~2 anos — o que significa que o teste de estabilidade também
  é um teste de regime, e os dois não podem ser separados.
- **Uma especificação vencedora escolhida entre ~32** (11 defasagens + 21 janelas)
  numa amostra que não cresce. Busca infla t-stat, e este é o principal risco do
  estudo. Mitigado pelos critérios 3 e 4 (estabilidade e plateau), não eliminado:
  se o resultado passar, ele ainda é uma hipótese sobrevivente, não um fato.
- **A defasagem de publicação do BCCh** só é observável hoje, não historicamente —
  o repositório não guarda vintages. Quanto de dianteira o sinal compra sai como
  estimativa a partir da defasagem corrente, não como fato medido.
- **Sem custo de transação.** Nada aqui é P&L; é medida de relação estatística.

## Fase 2 (fora de escopo, registrada)

Se a fase 1 for positiva: o fluxo previsto antecipa o USDCLP?

Desenho já decidido, para não se perder: residualizar o retorno diário do USDCLP
nas variações diárias dos três fatores do modelo CLP da mesa (`LP1 Comdty`,
`CHSWP1 Curncy`, `DXY Curncy`) com janela móvel — **não** usando os coeficientes do
`modelo_clp()` de `R:\Macro EMs\EMs\FX Models\gerar_dashboard_fx.py`, que são
ajustados em janela fixa 2022–2026 e aplicados ao histórico inteiro, o que é
look-ahead para fins de backtest. Medir o IC de Spearman do fluxo previsto contra
o resíduo acumulado em t+1, t+5, t+10 e t+21, com piso no momentum do próprio CLP
e teto no IC do fluxo realizado.
