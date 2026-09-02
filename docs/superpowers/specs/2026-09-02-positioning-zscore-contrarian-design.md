# Níveis esticados de positioning como sinal contrarian para o CLP — desenho

Data: 2026-09-02
Status: aprovado, pronto para plano de implementação

## Hipótese

Posição lotada se desfaz. Se o mercado está muito comprado em USD contra o CLP,
os compradores marginais já compraram: sobra pouca demanda para empurrar o par
mais para cima e muita posição para ser estopada na primeira virada. A partir de
algum nível de posicionamento, portanto, o retorno esperado do USDCLP inverte de
sinal — o nível esticado vira sinal **contrarian**.

O nível bruto em USD não serve para medir isso: o tamanho do balanço de cada setor
muda com o tempo, e −8.000 mm em 2022 não significa o mesmo que −8.000 mm em 2026.
A medida precisa ser **normalizada**: quantos desvios-padrão a posição de hoje está
da posição típica recente.

A pergunta operacional: existe um valor de z a partir do qual o retorno futuro
esperado do USDCLP muda de sinal, e esse valor sobrevive a testes de falsificação?

## Escopo

**Dentro.** Um módulo de pesquisa offline que mede se o efeito existe. Produz um
relatório HTML. Além disso, uma função de z-score point-in-time em
`src/data_processor.py` — a única alteração em `src/`, feita aqui porque a fase 2
vai reusá-la.

**Fora.** Qualquer aba, gráfico ou texto do painel. O estudo consome o painel como
biblioteca.

**Fora, adiado para a fase 2.** Replicar no painel cada gráfico de nível em USD com
um gráfico de z-score logo abaixo. Registrado no fim deste documento.

**Fora, deliberadamente.** O z-score do *fluxo* (variação da posição). A pergunta
aqui é sobre nível esticado, não sobre momentum de fluxo. São hipóteses diferentes
e misturá-las gastaria o pouco poder estatístico que a amostra tem.

## Dados

Tudo já disponível via `data_processor.build_fx_dados()`: séries do BCCh mais o
fechamento do USDCLP. Nenhuma fonte nova.

### Amostra

O BCCh devolve essas séries a partir de **2022-01-03**, e só. Pedir data inicial
mais antiga não traz nada — foi verificado. São ~1.150 pregões até hoje.

Com o burn-in de 252 pregões da janela rolante, o z-score só existe de ~jan/2023
em diante: **~900 observações úteis**. Esse número é a restrição central do estudo
e a razão de o desenho priorizar falsificação sobre otimização.

### Séries testadas

Todas em **convenção compra-de-USD**: acima de zero = comprando USD. Duas entram
invertidas em relação ao dado bruto do BCCh, exatamente como já fazem as abas do
painel.

| Coluna em `build_fx_dados()` | Nome no estudo | Inverter sinal? |
|---|---|---|
| `Fondos de pensiones` | Fundos de Pensão | sim |
| `No residentes` | Offshore | sim |
| `Empresas sector real` | Corporate | não |
| `PosicaoBancos` | Bancos | não |
| soma das duas primeiras (já invertidas) | Total (Pensões + Offshore) | — |

As quatro séries setoriais são ligadas por identidade contábil: o que um setor
compra, outro vendeu. Isso não invalida testá-las individualmente, mas significa
que resultados espelhados entre elas são esperados, não confirmatórios. O teste de
espelho na seção de falsificação existe para separar as duas coisas.

### Variável dependente

Retorno log forward do USDCLP, em pontos percentuais:

```
r[t, h] = 100 * (ln USDCLP[t+h] - ln USDCLP[t])
```

com `h` em {5, 21, 63} pregões. Positivo = CLP depreciou.

A hipótese contrarian prevê **sinal negativo de `r` nos buckets de z alto**: posição
comprada em USD e lotada, seguida de apreciação do CLP.

Os `h` últimos pregões da amostra não têm `r[t, h]` definido e saem do cálculo. Não
se preenche com nada.

## Normalização

Z-score de janela rolante de 252 pregões, calculado **point-in-time**:

```
z[t] = (x[t] - media(x[t-251 : t])) / desvio(x[t-251 : t])
```

A janela é fechada em `t` e inclui o próprio `x[t]`. Nada posterior a `t` entra.

Regras de borda:

- Os primeiros 251 pregões de cada série produzem `NaN` (janela incompleta).
- Desvio-padrão amostral (`ddof=1`).
- Se o desvio for menor que `1e-9`, o `z` daquela data é `NaN` em vez de explodir.
- `NaN` no meio da série (feriado do BCCh sem publicação) reduz a janela efetiva;
  exige-se um mínimo de 200 observações válidas na janela, senão `NaN`.

A função vive em `src/data_processor.py` como `rolling_zscore(serie, janela=252,
min_obs=200)`, recebendo e devolvendo `pd.Series`. É a peça compartilhada com a
fase 2.

## Teste principal: buckets e curva dose-resposta

Buckets fixos, definidos **antes** de olhar o dado, para que não haja escolha de
corte a posteriori:

| Bucket | Faixa de z | Leitura |
|---|---|---|
| `muito_short` | `z < -2` | posição vendida em USD, esticada |
| `short` | `-2 <= z < -1` | vendida |
| `neutro` | `-1 <= z <= 1` | sem informação |
| `long` | `1 < z <= 2` | comprada |
| `muito_long` | `z > 2` | comprada em USD, esticada |

Os buckets são exaustivos e mutuamente exclusivos por construção; um teste garante
isso.

Para cada série × bucket × horizonte, o relatório traz:

- média de `r[t, h]`
- número de observações
- **número de episódios independentes**: blocos contíguos de datas dentro do bucket,
  separados por pelo menos um pregão fora dele
- intervalo de confiança de 90% por **block bootstrap circular**, blocos de tamanho
  `h`, 5.000 repetições, semente fixa

O bootstrap por blocos é obrigatório, não um refinamento: com `h = 63`, observações
consecutivas compartilham 62 dos 63 dias de retorno. Um intervalo de confiança
i.i.d. seria estreito demais por um fator grande e transformaria ruído em achado.

A leitura do resultado é a **forma da curva**, não um bucket isolado: o efeito é
crível se a média de `r` decresce monotonicamente do bucket `muito_short` ao
`muito_long` e se as pontas caem fora do intervalo do bucket neutro. Bucket extremo
significante com o meio embaralhado é ruído bem vestido.

## Falsificação

Quatro guardas. Todas rodam sempre e todas entram no relatório, inclusive — e
principalmente — quando o resultado principal é bonito.

1. **Espelho contábil.** Correlação entre a curva dose-resposta de cada par de
   setores. Se Corporate e Bancos entregam o negativo exato de Pensões e Offshore,
   o que se mediu foi a identidade contábil do mercado cambial, não capacidade
   preditiva. O relatório mostra as curvas lado a lado.

2. **Placebo por embaralhamento em blocos.** 1.000 repetições em que a série de `z`
   é embaralhada em blocos de 21 pregões (preservando a autocorrelação, destruindo
   o alinhamento com o retorno futuro). Produz a distribuição nula do maior efeito
   entre buckets. Se o efeito observado cai dentro dessa distribuição, não há
   achado — mesmo que o bootstrap tenha dado intervalo bonito.

3. **Contagem de episódios.** Bucket extremo com menos de 5 episódios independentes
   é rotulado como anedota no relatório, com o rótulo visível junto ao número, e não
   sustenta conclusão. Com ~900 observações e séries persistentes, esse caso é
   provável, não hipotético.

4. **Vazamento.** Teste unitário que constrói uma série com um salto conhecido e
   confirma que `z[t]` não muda quando qualquer valor posterior a `t` é alterado.
   Segundo teste confirma que `r[t, h]` nunca entra no cálculo de `z`.

## Estrutura

Segue o padrão do estudo `afp_leading`.

```
estudos/positioning_zscore/
  dados.py          # carrega via data_processor, aplica convenção de sinal, calcula z e retornos forward
  buckets.py        # atribuição de bucket, médias por bucket, episódios, block bootstrap
  falsificacao.py   # espelho contábil, placebo, contagem de episódios
  relatorio.py      # HTML na casca JGP
  __main__.py       # entrypoint: python -m estudos.positioning_zscore
  saida/positioning_zscore.html

tests/positioning_zscore/
  test_dados.py
  test_buckets.py
  test_falsificacao.py
```

Cada módulo tem uma responsabilidade e uma interface pequena: `dados.py` devolve um
DataFrame longo com `Data`, `serie`, `nivel`, `z`, `r_5`, `r_21`, `r_63`;
`buckets.py` consome esse DataFrame e devolve a tabela de resultados;
`falsificacao.py` consome os mesmos dois e devolve os diagnósticos. `relatorio.py`
não calcula nada — só formata.

## Testes

Escritos antes da implementação. Os que importam:

- `rolling_zscore` reproduz o valor calculado à mão numa série pequena
- `rolling_zscore` devolve `NaN` no burn-in, com desvio nulo e com poucas observações
- alteração de dado futuro não muda `z` em `t` (vazamento)
- `r[t, h]` alinha com o USDCLP `h` pregões à frente, e é `NaN` nas últimas `h` linhas
- buckets exaustivos e mutuamente exclusivos, e as bordas (`z = -2`, `z = -1`,
  `z = 1`, `z = 2`) caem no bucket que a tabela declara
- contagem de episódios: série sintética com dois blocos separados devolve 2, não o
  total de dias
- block bootstrap é reprodutível com semente fixa

## Decisões assumidas

- Horizontes 5, 21 e 63 pregões (1 semana, 1 mês, 1 trimestre de pregões).
- Teste **univariado**: sem controlar por DXY, cobre ou diferencial de juros. Com
  ~900 observações, cada controle adicional gasta poder que não existe. Se o efeito
  sobreviver, controlar vira a pergunta da fase seguinte.
- Janela de 252 pregões, escolhida antes de ver resultado. Não se varre a janela
  em busca da que funciona — isso é garimpo, e o desenho inteiro existe para evitá-lo.

## Fase 2 — painel (não implementar aqui)

Replicar no painel cada gráfico de nível em USD com um gráfico de z-score logo
abaixo, usando a mesma `rolling_zscore` de 252 pregões. Gráficos de nível hoje:
`pension_line`, `offshore_line`, `corporate_line`, `banks_line`, o nível da aba
Offshore Ajustado e os níveis acumulados da aba Fluxo AFP. Spec própria, depois que
este estudo disser se as faixas de z merecem marcação visual (linhas em ±1 e ±2) ou
se são só uma escala.
