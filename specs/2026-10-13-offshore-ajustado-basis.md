# Offshore Ajustado: desconto do basis trade pelo excesso de spot

13-out-2026. Muda a conta da aba *Offshore Ajustado*. Os gráficos são os mesmos;
muda só a série ajustada.

## A ideia

O NDF oficial do offshore mistura posição especulativa com hedge de basis trade:
o estrangeiro vende USD no spot, compra papel curto em CLP (PDBC, BTP) e se
protege comprando USD no NDF. Esse long USD no NDF não é aposta no câmbio. O
ajuste tira do NDF um estoque estimado de basis trades.

## Antes e depois

| | Antes (até 13-out-2026) | Agora |
|---|---|---|
| Âncora | 15-dez-2025 | **27-out-2025** |
| O que conta como basis | toda venda spot líquida do offshore | só a venda **acima de USD 10 mn/dia** |
| Estoque de basis em 08-out-2026 | 11,9 bi | 12,8 bi |
| Ajustado (long USD) em 08-out-2026 | 8,1 bi | 7,3 bi |

```
estoque_basis(t) = soma desde 27-out-2025 de (venda spot NR(d) - 10)
ajustado(t)      = NDF oficial long USD(t) - estoque_basis(t)
```

Séries do BCCh: NDF `F099.DER.STO.Z.40.N.NR.NET.Z.MMUSD.MLME.Z.Z.0.D` e spot
`F099.SPT.FLU.Z.40.N.NR.NET.Z.MMUSD.MLME.Z.Z.0.D` (positivo = offshore vende USD).
Parâmetros em `src/config.py` (`OFFSHORE_ADJ_CUTOVER`, `OFFSHORE_ADJ_SPOT_BASE`).

## Por que mudar

1. **Âncora.** A rodada de basis trades começou no fim de out/2025. Começando em
   15-dez, ficavam fora do estoque os ~USD 3,4 bi vendidos no spot entre 27-out e
   12-dez, e o ajustado ficava alto demais.
2. **Excesso, não spot cheio.** Nem toda venda spot do estrangeiro é basis: há
   entrada de ações e renda fixa sem hedge, IED e fluxos correntes, que são
   posição de verdade. Tratar todo o spot como basis descontava ~USD 10 mn/dia a
   mais (~2,4 bi/ano) e puxava o ajustado para baixo com o tempo.

Os dois efeitos vão em sentidos opostos e quase se anulavam no fim da amostra
(8,1 vs 7,3 bi). No caminho, porém, a diferença chegou a 2–3 bi, e em fev/2026 os
sinais ficavam trocados: a conta nova mostra o offshore vendido em USD (~−1,8 bi)
e a antiga, comprado (~+1 bi).

## Ressalvas

- O ritmo "normal" de 10 mn/dia é um parâmetro, não um dado observado. Valores
  entre 9 e 11 e âncoras entre 20 e 28-out dão séries praticamente iguais. Em
  2023–2025 o offshore foi, em média, comprador líquido de USD no spot (~20/dia),
  então esse "normal" é discutível.
- Os gráficos de pernas da aba (5 pregões, rolantes) seguem mostrando o spot
  observado, sem o desconto. O net das pernas difere da variação do ajustado em
  10 mn por pregão (50 por bloco de 5).
- Antes de 27-out-2025 a série é só o NDF, então o nível antes e depois da
  âncora não é comparável.
