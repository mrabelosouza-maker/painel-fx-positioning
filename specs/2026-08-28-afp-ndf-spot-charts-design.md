# Aba NDF + Spot dos AFPs: net, evolucao das pernas e razao de hedge

Data: 2026-08-28

## Problema

A aba mostra hoje o acumulado de 7 dias das duas pernas, uma tabela dos ultimos
cinco dias e um grafico de barras semanais. Falta:

- o **net** das duas pernas, que so aparece na tabela e nao em nenhum grafico;
- a **evolucao no tempo** de cada perna, que hoje so existe agregada por semana;
- quanto do fluxo spot os AFPs de fato **hedgeiam** com o forward.

## Layout final da aba

| Linha | Painel | Estado |
|-------|--------|--------|
| 1 | Barras de 7 dias (wide) + tabela e nota (narrow) | inalterado |
| 2 | Semanal: barras NDF e spot **+ linha de net** | modificado |
| 3 | `NDF: nivel do saldo` ǀ `SPOT: fluxo diario` — lado a lado | novo |
| 4 | `NET diario: dNDF + spot` | novo |
| 5 | `Razao de hedge`: barras semanais + linha movel de 13 semanas | novo |

Vai do curto prazo ao estrutural, de cima para baixo. Nenhuma fonte nova: tudo
sai das duas series do BCCh que a aba ja busca.

## Series novas

`build_afp_spot_flow` passa a devolver duas colunas que ela hoje calcula e
descarta:

- `ndf_level` — o nivel cru do saldo forward do setor 42. Positivo = AFP net
  short USD, que ja e a convencao compra-de-CLP da aba.
- `net_1d` = `ndf_1d + spot_bcch`, com `min_count=1`, a mesma regra da coluna
  `Net (NDF+spot)` da tabela, para grafico e tabela nao discordarem.

`build_afp_weekly_legs` ganha:

- `net_wk` = `ndf_wk + bcch_wk`
- `hedge_wk` = `-ndf_wk / bcch_wk`
- `hedge_cum` = `-cumsum(ndf_wk) / cumsum(bcch_wk)`

## Razao de hedge: convencao de sinal

O AFP compra USD spot para mandar dinheiro para fora, o que na convencao da aba
e perna spot **negativa**. Hedgear isso e vender esse USD a termo, o que aumenta
o net short USD, ou seja perna NDF **positiva**. Hedge = as duas pernas com
sinais opostos, e por isso a razao leva o sinal de menos:

    hedge = - ndf / spot

- spot -100, NDF +100 -> +100%, integralmente hedgeado
- spot -100, NDF 0     ->    0%, aberto
- spot -100, NDF -50   ->  -50%, o forward **amplia** a aposta em vez de hedgear

Funciona nos dois sentidos: se o AFP repatria (spot +100) e desmonta o forward
(NDF -100), da +100% igual.

Semana com fluxo spot pequeno demais vira NaN: uma razao sobre denominador de 2
MM USD nao carrega informacao, so estoura a escala. Piso de 25 MM USD (percentil
10 de `|spot|` semanal e 20), que corta 25 das 222 semanas.

## Por que a linha e acumulada e nao uma janela movel

A primeira versao usava janela movel de 13 semanas. Nela **58% dos trimestres
davam mais de 100%**, o que torna a leitura de "sobre-hedge" sem sentido — e a
causa nao e ruido de denominador: testando, a razao entre fluxo liquido e bruto
de spot e 0,68 nos trimestres acima de 100% e 0,69 nos abaixo (correlacao -0,28
com a razao). O problema e conceitual.

O numerador e a variacao de um **estoque**: o saldo forward cobre toda a carteira
offshore, hoje 33,5 bn USD, e ela se move por conta propria — a carteira se
valoriza e exige mais forward com zero de spot novo, o AFP sobe a fatia hedgeada
do que ja tem, renda offshore e reinvestida la fora. O denominador e o **fluxo**
do periodo, mediana de 1,6 bn por trimestre. Basta o estoque andar 5% para o
delta de NDF do trimestre valer 100% do spot. Regredindo, o fluxo spot explica
R2=0,54 do delta de NDF e o nivel previo do NDF explica R2=0,30: o spot e o
driver dominante, mas longe de ser o unico.

No acumulado os dois se comparam na mesma base. No periodo inteiro o saldo
forward foi de 13,6 para 33,5 bn (+19,9) contra 22,4 bn de compra liquida de USD
no spot: **89%**, abaixo de 100% e interpretavel. Hoje a linha esta em 88,7%, e
so 9% dos pontos passam de 100% contra os 58% da versao movel.

A linha so entra quando `|cumsum(bcch_wk)|` passa de 2000 MM USD, da ordem de um
trimestre de fluxo bruto (a soma de 13 semanas de `|spot|` tem mediana 2518). Ate
meados de 2023 o acumulado era menor que isso e trocava de sinal, e a razao ia de
-130% a +322% sem significar nada. Com o piso a linha comeca em jun/2023 e daí em
diante e continua: o acumulado nunca mais volta a ficar abaixo dele. Na faixa
exibida ela vai de -86% a +96%, sem nenhum ponto acima de 100%.

O caminho anual tem leitura propria: -70% no fim de 2023, +32% em 2024, +84% em
2025, +89% agora. A cobertura vinha sendo reconstruida ao longo do periodo, e
parte dessa subida e convergencia mecanica do acumulado.

## Graficos

Em `chart_builder.py`:

- `make_afp_weekly_bars` ganha um `go.Scatter` de net sobre as barras, linha
  preta com marcador losango — o mesmo tratamento que o grafico de decomposicao
  removido usava para o total.
- `make_afp_daily_bars(df, col, title, color)`, uma funcao so, serve os paineis
  de spot e de net: sao o mesmo grafico com coluna e cor diferentes, ambos em
  compra-de-CLP com os rotulos de lado.
- `make_afp_level_line(df)` para o nivel do NDF. Fica **sem** os rotulos de
  lado: ali acima de zero significa "AFP net short USD", que e estoque e nao
  fluxo, e reaproveitar o rotulo de fluxo confundiria. A leitura vai no titulo.
- `make_afp_hedge_ratio(wk, title)`: barras de `hedge_wk` em cinza claro atras,
  linha de `hedge_cum` por cima, linha de referencia em 100%.

Os dois paineis da linha 3 tem eixos independentes por natureza (30.000 contra
+-100), entao ficam lado a lado sem eixo compartilhado. Todos abrem no historico
todo desde jun/2022, com o zoom do Plotly para aproximar, seguindo o eixo
categorico que o resto do painel ja usa.

O eixo do grafico de hedge e limitado aos percentis 5 e 95 das barras semanais,
com folga, e sempre contendo a linha acumulada inteira: sem isso uma semana de
denominador pequeno achata todo o resto. As barras que saem da faixa ficam
cortadas, e o titulo diz que a linha e o que se le.

## Resultado

A razao acumulada esta em **89%**: desde jun/2022 os AFPs cobriram com forward
quase todo o dolar que compraram no spot.

## Fora de escopo

- O hedge ratio proprio, `nivel do NDF / ativos offshore`, que e a pergunta que
  a razao acumulada so aproxima. Exige o AUM offshore por tipo de fundo, que
  vinha do `Fundos de Pensao.xlsx` que saiu do build no commit anterior.
- Calibrar a defasagem entre a perna spot e a perna de NDF (o hedge pode ser
  montado dias depois da compra do dolar).
- Separar o fluxo spot dos AFPs por destino (renda fixa vs variavel offshore).
