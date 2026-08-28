# Aba Todos os Setores: NDF + spot

Data: 2026-08-28

## Problema

O painel tratava NDF e spot juntos so para fundos de pensao e para o offshore,
cada um na sua aba. Nao havia lugar para ver os oito setores lado a lado e
responder quem esta comprando e quem esta vendendo CLP no agregado.

## O que o BCCh publica

Verificado: `SPT.FLU` existe para **todos** os setores que tem saldo de NDF, nao
so os dois que o painel ja usava. Entao a aba sai inteira de dados publicados,
sem proxy.

## Armadilha dos codigos R.55A e R.63

A descricao de serie do BCCh e um **caminho hierarquico**, nao um nome:

    R.55A -> "Empresas sector real | Residentes no bancos, Monto vigente neto"
    R.63  -> "Residentes no bancos | Monto vigente neto"

Le-se: R.55A e a folha, que fica sob R.63, que e o agregado. Vale igual nos dois
namespaces (`DER.STO` e `SPT.FLU`).

Os comentarios inline do `SERIES_FX` diziam o contrario ("R.55A = Residentes no
bancos"), e ainda por cima um deles falava em usar um como proxy do outro. O
`SERIES_NAMES_ALL` sempre esteve certo, porque atribui nome por posicao, entao o
painel nunca mostrou dado trocado — mas o comentario derrubou a primeira versao
desta aba, em que o spot das folhas nao fechava com o agregado (-896,7 contra
-196,0 em 7 dias). Comentarios corrigidos.

**Teste que pega isso:** somar as seis folhas tem que dar `Residentes no bancos`
exato. Roda a cada build, para NDF, spot e net, nas tres janelas.

## Hierarquia

    Monto vigente neto (total)
    |- No residentes
    `- Residentes no bancos (agregado, nao e setor)
       |- Fondos de pensiones
       |- Companias de seguros
       |- Empresas sector real
       |- Corredoras de bolsa
       |- Adm generales de fondos
       `- Otros sectores

Diferenca media entre soma das folhas e agregado: 0,00 MM USD.

## Layout

| Linha | Painel |
|-------|--------|
| 1 | Grafico de linhas: net semanal por setor |
| 2 | Tabela de 1 dia ǀ tabela de 7 dias |
| 3 | Tabela de 28 dias ǀ nota de como ler |

Uma tabela por horizonte em vez de uma tabela larga com grupos de coluna: cabe
na tela sem rolagem horizontal e da para copiar uma janela inteira para um
e-mail.

Colunas: setor, delta de NDF na janela, spot acumulado na janela, net, e o saldo
de NDF no fim da janela para dar contexto de tamanho. As folhas vao indentadas e
os agregados em negrito com risco em cima, para a conta ficar visivel na propria
tabela.

Todas as janelas fecham na **mesma data**, a ultima com dado. Se cada setor
fechasse na sua, a linha de total nao fecharia.

## Grafico

Net semanal empilhado, uma barra por setor: as seis folhas mais o offshore. Os
agregados intermediarios ficam de fora, sao soma das folhas e contariam duas
vezes.

Empilhado e nao linhas porque a pergunta da aba e de composicao — quem compra e
quem vende CLP na semana — e sete linhas cruzando zero nao mostram isso. Com
`barmode="relative"` os compradores empilham para cima e os vendedores para
baixo.

O total vai como losango preto e nao como barra: numa pilha com sinais dos dois
lados a altura liquida nao e visivel, e o marcador mostra onde as duas pilhas se
encontram. Ele sai da soma das proprias barras, nao da serie de total publicada,
entao e por construcao o que se ve somando o desenho (as duas batem, 0,0000).

O eixo vem da soma dos positivos e da soma dos negativos da semana, nao do maior
setor isolado: numa pilha o alcance e a soma. Nas ultimas 26 semanas isso da
4693 para cima e 4919 para baixo, contra um setor isolado que raramente passa de
2000.

Abre nas ultimas 26 semanas; duplo-clique devolve o historico todo e clicar na
legenda isola um setor.

## Convencao

Acima de zero = compra de CLP, igual ao resto do painel. As duas series do BCCh
vem na otica do banco residente, que ja e essa convencao, entao entram sem
inverter sinal.

## Fora de escopo

- Decompor o spot por moeda ou por prazo.
- Serie de nivel para o spot: o BCCh so publica `SPT.STO` para o total (`Z.Z`),
  os setores tem so fluxo. Verificado: `SPT.STO` por setor devolve Codigo=-50.
