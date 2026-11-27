import cv2
import numpy as np


def _binarizar(imagem):
    cinza = cv2.cvtColor(imagem, cv2.COLOR_RGB2GRAY)
    return cv2.adaptiveThreshold(
        cinza, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 51, 12
    )


def _horizontais(binaria):
    h, w = binaria.shape
    mascara = cv2.morphologyEx(
        binaria, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (max(1, w // 6), 1))
    )
    _, rotulos, stats, _ = cv2.connectedComponentsWithStats(mascara)
    linhas = []
    for i, (x, y, largura, altura, _) in enumerate(stats[1:], 1):
        if largura > w * 0.65 and altura < h * 0.025:
            linhas.append((y + altura // 2, i))
    return sorted(linhas), rotulos


def _grupo_linhas(linhas, altura):
    ys = [y for y, _ in linhas]
    distancias = np.diff(ys)
    candidatas = distancias[(distancias > altura * 0.008) &
                            (distancias < altura * 0.035)]
    if len(candidatas) < 3:
        raise ValueError('Linhas da tabela nao identificadas.')
    passo = float(np.median(candidatas))
    grupos = [[ys[0]]]
    for anterior, atual in zip(ys, ys[1:]):
        if 0.7 * passo <= atual - anterior <= 1.3 * passo:
            grupos[-1].append(atual)
        else:
            grupos.append([atual])
    grupo = max(grupos, key=len)
    if len(grupo) < 4:
        raise ValueError('Tabela fora do padrao esperado.')
    if len(grupos) > 1 and sum(len(g) == len(grupo) for g in grupos) > 1:
        raise ValueError('Mais de uma tabela candidata; revisar pagina.')
    return grupo


def detectar_tabela(imagem: np.ndarray) -> dict:
    """Recebe RGB; devolve imagem alinhada e caixas (x1,y1,x2,y2)."""
    h, w = imagem.shape[:2]
    linhas, rotulos = _horizontais(_binarizar(imagem))
    grupo = _grupo_linhas(linhas, h)
    # Estima a inclinacao das linhas reais da tabela.
    angulos = []
    for y, indice in linhas:
        if y in grupo:
            yy, xx = np.where(rotulos == indice)
            vx, vy, _, _ = cv2.fitLine(
                np.column_stack((xx, yy)).astype(np.float32),
                cv2.DIST_L2, 0, 0.01, 0.01
            ).ravel()
            angulos.append(np.degrees(np.arctan(float(vy) / float(vx))))
    angulo = float(np.median(angulos))
    matriz = cv2.getRotationMatrix2D((w / 2, h / 2), angulo, 1)
    alinhada = cv2.warpAffine(imagem, matriz, (w, h), borderValue=(255, 255, 255))

    binaria = _binarizar(alinhada)
    linhas, _ = _horizontais(binaria)
    ys = _grupo_linhas(linhas, h)
    topo, base = ys[0], ys[-1]
    recorte = binaria[topo:base, :]
    vertical = cv2.morphologyEx(
        recorte, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(1, (base - topo) // 4)))
    )
    _, _, stats, _ = cv2.connectedComponentsWithStats(vertical)
    xs = sorted(int(x + largura // 2) for x, _, largura, altura, _ in stats[1:]
                if altura > 0.65 * (base - topo) and largura < w * 0.025)
    if len(xs) != 3 or min(np.diff(xs)) < w * 0.2:
        raise ValueError(f'Esperadas 3 divisorias verticais; encontradas {len(xs)}.')
    esquerda, meio, direita = xs
    alunos = []
    for i, (y1, y2) in enumerate(zip(ys, ys[1:]), 1):
        alunos.append({'linha': i,
                       'nome': (esquerda, y1, meio, y2),
                       'assinatura': (meio, y1, direita, y2)})
    return {'imagem': alinhada, 'alunos': alunos,
            'tabela': (esquerda, topo, direita, base), 'angulo': angulo}
