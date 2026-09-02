"""Entrypoint do estudo. Encadeia dados -> modelo -> avaliacao -> relatorio.

    python -m estudos.afp_leading.rodar

Escolha da especificacao vencedora: maior R2 fora de amostra entre as
UTILIZAVEIS. Nao a de maior R2 dentro de amostra — dentro de amostra a
especificacao mais flexivel sempre ganha, e o que interessa e prever.
"""
import logging
from pathlib import Path

from .dados import montar_painel
from .modelo import Spec, estrutura_defasagem, beta_movel, portao_sanidade
from .avaliacao import previsao_oos, avaliar, tem_plateau
from .relatorio import gerar

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ALVO = "net_1d"
PREDITOR = "r_MXWO"
SAIDA = Path(__file__).resolve().parent / "saida" / "afp_fluxo_previsto.html"


def main() -> int:
    painel = montar_painel()
    logger.info("Painel com %d observacoes", len(painel))

    tab = estrutura_defasagem(painel, ALVO, PREDITOR)
    utilizaveis = tab[tab["utilizavel"]]
    if utilizaveis.empty:
        raise RuntimeError("nenhuma especificacao utilizavel")

    # Portao de sanidade na melhor candidata dentro de amostra, antes de gastar
    # as ~32 avaliacoes fora de amostra (cada uma roda uma OLS por dia).
    melhor_dentro = utilizaveis.loc[utilizaveis["r2"].idxmax()]
    ok_portao, msg_portao = portao_sanidade(float(melhor_dentro["beta"]))
    logger.info("Portao de sanidade: %s | %s", "OK" if ok_portao else "FALHOU", msg_portao)

    aval_por_spec = {}
    for row in utilizaveis.itertuples():
        a = avaliar(painel, Spec(ALVO, PREDITOR, row.tipo, row.n))
        aval_por_spec[(row.tipo, row.n)] = {"r2_oos": a["r2_oos"], "beta": row.beta, "aval": a}
        logger.info("%s n=%d: beta %.0f, R2 OOS %.3f", row.tipo, row.n, row.beta, a["r2_oos"])

    (tipo_v, n_v) = max(aval_por_spec, key=lambda k: aval_por_spec[k]["r2_oos"])
    spec = Spec(ALVO, PREDITOR, tipo_v, n_v)
    aval = aval_por_spec[(tipo_v, n_v)]["aval"]
    logger.info("Vencedora: %s n=%d, R2 OOS %.3f", tipo_v, n_v, aval["r2_oos"])

    ok_plateau, msg_plateau = tem_plateau(tab, tipo_v, n_v, aval_por_spec)
    m = aval["metades"]
    b1, b2 = m["primeira"]["beta"], m["segunda"]["beta"]
    mesmo_sinal = (b1 < 0) == (b2 < 0)
    razao = max(abs(b1), abs(b2)) / min(abs(b1), abs(b2)) if min(abs(b1), abs(b2)) > 0 else float("inf")
    ok_estabilidade = mesmo_sinal and razao <= 2.0
    ok_r2 = aval["r2_oos"] > 0.10

    criterios = [
        ("1. Portao de sanidade (beta negativo, h*A plausivel)", ok_portao, msg_portao),
        ("2. R2 fora de amostra > 0,10", ok_r2, f"R2 OOS = {aval['r2_oos']:.3f}"),
        ("3. Estabilidade nas duas metades (mesmo sinal, razao <= 2x)", ok_estabilidade,
         f"beta {b1:,.0f} e {b2:,.0f}, razao {razao:.2f}x"),
        ("4. Plateau (vizinhos vivos na grade)", ok_plateau, msg_plateau),
    ]
    veredito = all(ok for _, ok, _ in criterios)

    bm = beta_movel(painel, spec)
    prev = previsao_oos(painel, spec)
    caminho = gerar(SAIDA, spec, tab, bm, prev, aval, criterios, veredito)

    logger.info("VEREDITO: %s", "POSITIVO" if veredito else "NEGATIVO")
    logger.info("Relatorio em %s", caminho)
    return 0 if veredito else 1


if __name__ == "__main__":
    raise SystemExit(main())
