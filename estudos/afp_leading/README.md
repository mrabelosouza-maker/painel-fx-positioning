# Fluxo AFP previsto a partir de bolsa global — resultado

Estudo em `estudos/afp_leading/`. Ver o desenho completo em
`docs/superpowers/specs/2026-09-02-afp-fluxo-previsto-design.md`.

## Hipótese

O rebalanceamento cambial dos fundos de pensão chilenos (AFP) é mecânico. O AFP
mantém uma carteira externa de valor `A` (em USD) e hedgeia uma fração `h` dela
contra o CLP. Quando a bolsa global sobe `r%`, a carteira externa vale `A(1+r)`
e, para manter a razão de hedge, o AFP precisa **vender `h·A·r` de USD a
termo**. O ajuste não seria instantâneo — viria com defasagem de dias.

Se verdadeira, o retorno de bolsa global (observável em tempo real) antecipa o
fluxo cambial do AFP, que o BCCh só publica com defasagem: a venda de dólar
já estaria batendo no mercado antes da confirmação oficial. Era uma hipótese
plausível porque o mecanismo de hedge de carteira é conhecido e o painel já
mostra o tamanho da posição: o saldo de NDF do setor 42 fecha
**2026-08-31 em USD -33,671 mm, ou seja, o AFP net short ~USD 33,7 bi em
forward** — o hedge existe e é grande.

## Veredito: NEGATIVO

Execução de referência: 2026-09-02, painel com 1.053 observações
(2022-06-02 a 2026-08-31), reprodução via `python -m estudos.afp_leading.rodar`.

Especificação vencedora (maior R² fora de amostra entre as utilizáveis):
alvo `net_1d`, preditor `r_MXWO`, defasagem **pontual k=4**.

| Métrica | Valor |
|---|---|
| β (dentro de amostra) | **+793,7** USD mm por unidade de retorno |
| R² fora de amostra | 0,001 |
| Correlação (previsto x realizado, OOS) | 0,062 |
| MAE fora de amostra | USD 76,4 mm |
| Observações na avaliação OOS | 797 |

### Os quatro critérios pré-registrados

| # | Critério | Resultado | Detalhe |
|---|---|---|---|
| 1 | Portão de sanidade (β negativo, h·A plausível) | **FALHOU** | β = +793,7 (positivo): bolsa subindo com o AFP comprando USD contraria o mecanismo de hedge |
| 2 | R² fora de amostra > 0,10 | **FALHOU** | R² OOS = 0,001 |
| 3 | Estabilidade nas duas metades (mesmo sinal, razão ≤ 2x) | PASSOU | β = +644,4 (1ª metade) e +955,0 (2ª metade), razão 1,48x |
| 4 | Plateau (vizinhos vivos na grade) | **FALHOU** | vizinho (pontual, k=3) tem R² OOS -0,003, menos da metade do vencedor — pico isolado |

Falhou 3 dos 4 critérios (1, 2 e 4). Não há terceira via: resultado
**NEGATIVO**.

## Auditoria de sinal

Antes de aceitar o resultado como achado econômico (e não como bug de
convenção), a cadeia de sinal foi verificada ponta a ponta contra o dado real:

- Há uma única inversão de sinal em todo o pipeline (a conversão da série
  crua do BCCh, que vem na ótica do banco residente, para a convenção de
  compra-de-USD do estudo) — e ela está no lugar certo, confirmada contra o
  saldo publicado.
- O painel mostra o AFP net short ~USD 33,7 bi em forward na última data
  disponível, que é o fato conhecido e batido contra o dado publicado pelo
  BCCh.
- O β saiu **positivo em 12 de 12 combinações alvo × preditor** testadas na
  auditoria. Não é um resultado isolado de uma escolha específica de série.

O negativo não é bug de convenção de sinal.

## Robustez a alvo e a preditor

O `rodar.py` agora aceita `--alvo` (`net_1d` ou `ndf_1d`) e `--preditor`
(`r_MXWO`, `r_MXWD`, `r_SPX` ou `r_MXEF`) por linha de comando. A tabela
abaixo roda as 8 combinações e reporta o β da melhor especificação **dentro
de amostra** (maior R² dentro de amostra entre as utilizáveis) para cada uma —
execução real em 2026-09-02, mesmo painel de 1.053 observações:

| Alvo | Preditor | Especificação | β (dentro de amostra) | R² dentro de amostra |
|---|---|---|---|---|
| `net_1d` | `r_MXWO` | acumulada w=5 | +542,3 | 0,0112 |
| `net_1d` | `r_MXWD` | acumulada w=5 | +557,0 | 0,0115 |
| `net_1d` | `r_SPX`  | acumulada w=6 | +421,3 | 0,0087 |
| `net_1d` | `r_MXEF` | acumulada w=4 | +449,3 | 0,0088 |
| `ndf_1d` | `r_MXWO` | acumulada w=4 | +468,1 | 0,0052 |
| `ndf_1d` | `r_MXWD` | acumulada w=4 | +483,9 | 0,0054 |
| `ndf_1d` | `r_SPX`  | acumulada w=4 | +340,2 | 0,0031 |
| `ndf_1d` | `r_MXEF` | acumulada w=2 | +675,9 | 0,0075 |

**As 8 combinações têm β positivo.** A conclusão não depende da escolha de
alvo (fluxo total `net_1d` vs. só a perna de hedge `ndf_1d`) nem da escolha de
índice de bolsa global. O sinal errado é um traço estrutural da amostra, não
um artefato de uma série específica.

## Leitura econômica

Nesta amostra, **o AFP compra USD quando a bolsa global sobe** — o oposto do
que o rebalanceamento passivo de hedge previria. Isso é compatível com
comportamento tático contra o CLP em ambiente de risk-on (por exemplo,
aproveitar força do CLP associada a risk-on global para montar posição
comprada em USD), e não com o ajuste mecânico de razão de hedge que a
hipótese original propunha.

A relação está estatisticamente presente no contemporâneo (k=0, não utilizável
para previsão porque o MXWO fecha depois do mercado cambial chileno) mas
**não é preditiva**: nenhuma defasagem utilizável (k≥1 ou janela acumulada)
produz poder de previsão fora de amostra que sobreviva ao critério de plateau.

## Limitações

- **1.053 observações, e não há mais.** É o limite do dado do BCCh
  (`BCENTRAL_FIRSTDATE = "2022-06-01"`), não uma escolha de configuração.
- **A especificação vencedora foi escolhida entre ~32** (11 defasagens
  pontuais + 21 janelas acumuladas) numa amostra que não cresce. Os critérios
  de estabilidade e plateau mitigam a busca por especificação, não a eliminam.
- Sem custo de transação: nada aqui é P&L, é medida de relação estatística.

## Como reproduzir

```
python -m estudos.afp_leading.rodar
python -m estudos.afp_leading.rodar --alvo ndf_1d --preditor r_MXEF
python -m pytest tests/afp_leading/ -v
```

O relatório HTML sai em `estudos/afp_leading/saida/afp_fluxo_previsto.html`
(fora do controle de versão — `estudos/*/saida/` está no `.gitignore`). Este
README é o registro versionado da conclusão.
