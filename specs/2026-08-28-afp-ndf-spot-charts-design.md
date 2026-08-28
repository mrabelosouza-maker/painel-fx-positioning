# Aba NDF + Spot dos AFPs: net e evolucao das pernas

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

## Razao de hedge: construida, e removida

Uma quinta linha da aba mostrava a fatia do fluxo spot coberta pelo NDF. Ela foi
construida, publicada e depois removida. O registro fica porque a razao da
remocao e o achado, nao o grafico.

**Convencao de sinal.** O AFP compra USD spot para mandar dinheiro para fora, o
que na convencao da aba e perna spot negativa; hedgear e vender esse USD a termo,
o que aumenta o net short e da perna NDF positiva. Hedge = sinais opostos, dai o
sinal de menos: `hedge = -ndf/spot`, com +100% cobertura integral e valor
negativo dizendo que o forward amplia a aposta em vez de proteger.

**Primeira versao, janela movel de 13 semanas.** 58% dos trimestres davam mais de
100%, o que torna a leitura de "sobre-hedge" sem sentido. A causa nao e ruido de
denominador: a razao entre fluxo liquido e bruto de spot e 0,68 nos trimestres
acima de 100% e 0,69 nos abaixo, correlacao -0,28 com a razao.

**O problema e conceitual, e nao tem conserto por reescala.** O numerador e a
variacao de um **estoque**: o saldo forward cobre toda a carteira offshore, hoje
33,5 bn USD, e ela se move por conta propria — a carteira se valoriza e exige
mais forward com zero de spot novo, o AFP sobe a fatia hedgeada do que ja tem,
renda offshore e reinvestida la fora. O denominador e o **fluxo** do periodo,
mediana de 1,6 bn por trimestre. Basta o estoque andar 5% para o delta de NDF do
trimestre valer 100% do spot. Regredindo, o fluxo spot explica R2=0,54 do delta
de NDF e o nivel previo do NDF explica R2=0,30: o spot e o driver dominante, mas
longe de ser o unico.

**Segunda versao, acumulada.** No acumulado os dois se comparam na mesma base: o
saldo forward foi de 13,6 para 33,5 bn (+19,9) contra 22,4 bn de compra liquida
de USD no spot, ou **89%**. A linha ficava com 168 pontos entre -86% e +96%,
nenhum acima de 100%, e so entrava quando o acumulado de spot passava de 2000 MM
USD, o que a fazia comecar em jun/2023.

**Por que saiu mesmo assim.** A versao acumulada e bem comportada, mas continua
respondendo a pergunta errada: ela mede co-movimento entre a variacao de um
estoque e um fluxo, e depende de um t0 arbitrario. O caminho anual (-70% no fim
de 2023, +32% em 2024, +84% em 2025, +89% agora) mistura mudanca real de
comportamento com convergencia mecanica do acumulado, e nao ha como separar as
duas. Um numero que so e legivel se o leitor souber tudo isso nao paga o espaco
que ocupa no painel.

O hedge ratio que responderia a pergunta e `nivel do NDF / ativos offshore`,
estoque contra estoque. Exige o AUM offshore por tipo de fundo, que vinha do
`Fundos de Pensao.xlsx` retirado do build. Fica registrado como o caminho certo
se o assunto voltar.

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

Os dois paineis da linha 3 tem eixos independentes por natureza (30.000 contra
+-100), entao ficam lado a lado sem eixo compartilhado. Todos abrem no historico
todo desde jun/2022, com o zoom do Plotly para aproximar, seguindo o eixo
categorico que o resto do painel ja usa.

## Fora de escopo

- O hedge ratio proprio, `nivel do NDF / ativos offshore`. Ver a secao sobre a
  razao de hedge removida.
- Calibrar a defasagem entre a perna spot e a perna de NDF (o hedge pode ser
  montado dias depois da compra do dolar).
- Separar o fluxo spot dos AFPs por destino (renda fixa vs variavel offshore).
