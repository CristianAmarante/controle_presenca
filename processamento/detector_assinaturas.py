"""Classificacao preliminar de campos de assinatura (fichas a 300 DPI).
Nao autentica assinaturas nem reconhece anotacoes administrativas.
Limiares experimentais, calibrados em tres fichas; validar em novas amostras.
"""
import cv2
import numpy as np


def classificar_assinatura(celula: dict) -> dict:
    original = celula['assinatura_original']
    tratada = celula['assinatura_tratada']
    linha = celula['linha']
    if (tratada.ndim != 2 or original.ndim != 3 or original.shape[2] != 3
            or min(tratada.shape) < 16 or original.shape[0] < 22
            or original.shape[1] < 30):
        return {'linha': linha, 'status': 'REVISAR',
                'motivo': 'Recorte fora do padrao', 'densidade_pct': None,
                'densidade_central_pct': None, 'ocupacao_central_pct': None,
                'ocupacao_total_pct': None, 'contraste_original_pct': None}

    h, w = tratada.shape
    binaria = (tratada < 128).astype(np.uint8)
    n, rotulos, stats, _ = cv2.connectedComponentsWithStats(binaria)
    manter = np.zeros(n, dtype=np.uint8)
    manter[1:] = stats[1:, cv2.CC_STAT_AREA] >= max(4, round(h*h*.002))
    tinta = manter[rotulos]
    centro = tinta[round(h*.22):round(h*.78), :]
    densidade = float(tinta.mean()*100)
    densidade_central = float(centro.mean()*100)
    ocupacao = float((tinta.sum(axis=0)>0).mean()*100)
    ocupacao_central = float((centro.sum(axis=0)>0).mean()*100)

    # Segunda medida: contraste local na imagem RGB original, incluindo tinta azul.
    bruto = np.min(original, axis=2)[3:-3, 7:-7].astype(np.uint8)
    fundo = cv2.GaussianBlur(bruto, (0, 0), sigmaX=12)
    marcas = fundo.astype(np.int16) - bruto.astype(np.int16) > 12
    altura = marcas.shape[0]
    contraste = float(marcas[round(altura*.25):round(altura*.75), :].mean()*100)

    if (2.2 <= densidade <= 25 and densidade_central >= 2.5
            and ocupacao_central >= 10 and ocupacao >= 12 and contraste >= 2.5):
        status, motivo = 'PRESENTE', 'Tracos distribuidos no interior da celula'
    elif (densidade <= .45 and densidade_central <= .65
          and ocupacao_central <= 3 and contraste <= .8):
        status, motivo = 'FALTA', 'Campo praticamente vazio ou marca pequena'
    else:
        status, motivo = 'REVISAR', 'Tracos ambiguos, fracos ou possivel invasao/anotacao'

    return {'linha': linha, 'status': status, 'motivo': motivo,
            'densidade_pct': round(densidade, 2),
            'densidade_central_pct': round(densidade_central, 2),
            'ocupacao_central_pct': round(ocupacao_central, 2),
            'ocupacao_total_pct': round(ocupacao, 2),
            'contraste_original_pct': round(contraste, 2)}


def detectar_assinaturas(celulas: list[dict]) -> list[dict]:
    """Recebe a saida de preprocessar_tabela, mantendo a linha fisica."""
    return [classificar_assinatura(c) for c in celulas]
