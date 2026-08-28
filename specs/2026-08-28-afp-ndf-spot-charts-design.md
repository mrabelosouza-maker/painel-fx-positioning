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
- `hedge_roll` = `-sum13(ndf_wk) / sum13(bcch_wk)`

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
MM USD nao carrega informacao, so estoura a escala. Os pisos saem dos quantis da
propria serie, um para cada janela:

| Janela | Piso | Percentil 10 do denominador | Observacoes cortadas |
|--------|------|-----------------------------|----------------------|
| semana | 25 MM USD | 20 MM USD | 25 de 222 |
| 13 semanas | 500 MM USD | 534 MM USD | 21 de 210 |

Com piso unico de 5 MM USD a razao semanal ia de -2501% a +2552% e o eixo
esmagava a linha movel; com 25 ela fica entre os percentis -242% e +521%, e a
linha ainda ocupa cerca de 70% da altura do painel.

A linha movel usa a razao das **somas** de 13 semanas, nao a media das razoes:
denominador grande o bastante para nunca estourar, e absorve o descasamento de
timing entre comprar o dolar e montar o forward. E a linha que responde a
pergunta estrutural; as barras semanais atras dela mostram a dispersao.

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
  linha de `hedge_roll` por cima, linha de referencia em 100%.

Os dois paineis da linha 3 tem eixos independentes por natureza (30.000 contra
+-100), entao ficam lado a lado sem eixo compartilhado. Todos abrem no historico
todo desde jun/2022, com o zoom do Plotly para aproximar, seguindo o eixo
categorico que o resto do painel ja usa.

O eixo do grafico de hedge e limitado aos percentis 5 e 95 das barras semanais,
com folga, e sempre contendo a linha movel inteira: sem isso uma semana de
denominador pequeno achata todo o resto. As barras que saem da faixa ficam
cortadas, e o titulo diz que a linha e o que se le.

## Resultado

Na mediana do historico a linha movel fica em **99%**: no trimestre os AFPs
hedgeiam com forward praticamente todo o dolar que compram no spot. O quartil
interno vai de 56% a 140%. As excursoes para fora disso sao trimestres em que as
duas pernas se descasam no tempo, nao mudanca de politica de hedge.

## Fora de escopo

- Calibrar defasagem entre a perna spot e a perna de NDF (o hedge pode ser
  montado dias depois da compra do dolar). A janela movel de 13 semanas absorve
  isso de forma grosseira; medir o lag e outro trabalho.
- Separar o fluxo spot dos AFPs por destino (renda fixa vs variavel offshore).
