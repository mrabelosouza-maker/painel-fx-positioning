"""Entrypoint do estudo. Encadeia dados -> modelo -> avaliacao -> relatorio.

    python -m estudos.afp_leading.rodar
    python -m estudos.afp_leading.rodar --alvo ndf_1d --preditor r_MXEF

Escolha da especificacao vencedora: maior R2 fora de amostra entre as
UTILIZAVEIS. Nao a de maior R2 dentro de amostra — dentro de amostra a
especificacao mais flexivel sempre ganha, e o que interessa e prever.
"""
import argparse
import logging
from pathlib import Path

import numpy as np

from .dados import montar_painel
from .modelo import Spec, estrutura_defasagem, beta_movel, portao_sanidade
from .avaliacao import previsao_oos, avaliar, tem_plateau
from .relatorio import gerar

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ALVO_PADRAO = "net_1d"
PREDITOR_PADRAO = "r_MXWO"
SAIDA = Path(__file__).resolve().parent / "saida" / "afp_fluxo_previsto.html"


def _parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--alvo", default=ALVO_PADRAO, choices=["net_1d", "ndf_1d"],
                   help=f"coluna de fluxo alvo (padrao: {ALVO_PADRAO})")
    p.add_argument("--preditor", default=PREDITOR_PADRAO,
                   choices=["r_MXWO", "r_MXWD", "r_SPX", "r_MXEF"],
                   help=f"coluna de retorno preditor (padrao: {PREDITOR_PADRAO})")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)
    ALVO, PREDITOR = args.alvo, args.preditor

    painel = montar_painel()
    logger.info("Painel com %d observacoes", len(painel))

    tab = estrutura_defasagem(painel, ALVO, PREDITOR)
    utilizaveis = tab[tab["utilizavel"]]
    if utilizaveis.empty:
        raise RuntimeError("nenhuma especificacao utilizavel")

    # Pre-screen barato na melhor candidata dentro de amostra, antes de gastar
    # as ~32 avaliacoes fora de amostra (cada uma roda uma OLS por dia). Isto
    # NAO e o criterio 1 da tabela de decisao: e so um portao para nao rodar o
    # resto quando o mecanismo claramente nao esta la. O criterio 1 de verdade
    # e recalculado abaixo sobre a especificacao vencedora (escolhida por R2
    # fora de amostra), que pode nao ser a mesma que "melhor_dentro".
    melhor_dentro = utilizaveis.loc[utilizaveis["r2"].idxmax()]
    ok_prescreen, msg_prescreen = portao_sanidade(float(melhor_dentro["beta"]))
    logger.info(
        "Pre-screen (melhor dentro de amostra, %s n=%d): %s | %s",
        melhor_dentro["tipo"], int(melhor_dentro["n"]),
        "OK" if ok_prescreen else "FALHOU", msg_prescreen,
    )

    aval_por_spec = {}
    for row in utilizaveis.itertuples():
        a = avaliar(painel, Spec(ALVO, PREDITOR, row.tipo, row.n))
        aval_por_spec[(row.tipo, row.n)] = {"r2_oos": a["r2_oos"], "beta": row.beta, "aval": a}
        logger.info("%s n=%d: beta %.0f, R2 OOS %.3f", row.tipo, row.n, row.beta, a["r2_oos"])

    # Filtra especificacoes com R2 OOS nao finito antes do max: toda comparacao
    # com NaN e False, entao um max ingenuo sobre o dict inteiro poderia eleger
    # uma especificacao NaN silenciosamente (ela "vence" so por vir primeiro).
    candidatas = {k: v for k, v in aval_por_spec.items() if np.isfinite(v["r2_oos"])}
    if not candidatas:
        raise RuntimeError("nenhuma especificacao com R2 fora de amostra finito")

    (tipo_v, n_v) = max(candidatas, key=lambda k: candidatas[k]["r2_oos"])
    spec = Spec(ALVO, PREDITOR, tipo_v, n_v)
    aval = aval_por_spec[(tipo_v, n_v)]["aval"]
    beta_vencedora = aval_por_spec[(tipo_v, n_v)]["beta"]
    logger.info("Vencedora: %s n=%d, R2 OOS %.3f", tipo_v, n_v, aval["r2_oos"])

    # Criterio 1 de verdade: portao de sanidade sobre a ESPECIFICACAO VENCEDORA,
    # nao sobre a melhor dentro de amostra do pre-screen acima.
    ok_portao, msg_portao = portao_sanidade(float(beta_vencedora))
    logger.info("Portao de sanidade (vencedora): %s | %s", "OK" if ok_portao else "FALHOU", msg_portao)

    # Passa so as UTILIZAVEIS (nao a tabela completa) para o teste de plateau:
    # a tabela completa inclui k=0, que nunca tem avaliacao (nao e utilizavel),
    # entao um vencedor em k=1 procuraria o vizinho k=0 e reprovaria por
    # "sem avaliacao" -- artefato de construcao, nao falha real de plateau.
    ok_plateau, msg_plateau = tem_plateau(utilizaveis, tipo_v, n_v, aval_por_spec)
    m = aval["metades"]
    b1, b2 = m["primeira"]["beta"], m["segunda"]["beta"]
    mesmo_sinal = (b1 < 0) == (b2 < 0)
    razao = max(abs(b1), abs(b2)) / min(abs(b1), abs(b2)) if min(abs(b1), abs(b2)) > 0 else float("inf")
    ok_estabilidade = mesmo_sinal and razao <= 2.0
    ok_r2 = aval["r2_oos"] > 0.10

    criterios = [
        (f"1. Portao de sanidade (beta negativo, h*A plausivel) "
         f"— especificacao vencedora ({tipo_v} n={n_v})", ok_portao, msg_portao),
        ("2. R2 fora de amostra > 0,10", ok_r2, f"R2 OOS = {aval['r2_oos']:.3f}"),
        ("3. Estabilidade nas duas metades (mesmo sinal, razao <= 2x)", ok_estabilidade,
         f"beta {b1:,.0f} e {b2:,.0f}, razao {razao:.2f}x"),
        ("4. Plateau (vizinhos vivos na grade)", ok_plateau, msg_plateau),
    ]
    veredito = all(ok for _, ok, _ in criterios)

    bm = beta_movel(painel, spec)
    bm_janela = beta_movel(painel, spec, janela=252)
    prev = previsao_oos(painel, spec)
    caminho = gerar(
        SAIDA, spec, tab, bm, bm_janela, prev, aval, criterios, veredito, len(painel),
        beta_vencedora=float(beta_vencedora),
    )

    logger.info("VEREDITO: %s", "POSITIVO" if veredito else "NEGATIVO")
    logger.info("Relatorio em %s", caminho)
    return 0 if veredito else 1


if __name__ == "__main__":
    raise SystemExit(main())
