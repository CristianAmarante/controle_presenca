"""Prepara as celulas detectadas para OCR e analise de assinaturas.

Entrada: dicionario de detectar_tabela(), com imagem RGB alinhada.
As imagens binarizadas tem fundo branco e tinta preta (uint8).
"""
import cv2
import numpy as np


def _normalizar(cinza: np.ndarray) -> np.ndarray:
    # Estima o fundo local para compensar sombras do escaneamento.
    fundo = cv2.GaussianBlur(cinza, (0, 0), sigmaX=18)
    return cv2.divide(cinza, np.maximum(fundo, 1), scale=255)


def _binarizar(cinza: np.ndarray, contraste: int) -> np.ndarray:
    return cv2.adaptiveThreshold(
        cinza, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 31, contraste
    )


def _recortar(imagem: np.ndarray, caixa: tuple, margem_x=0, margem_y=0):
    x1, y1, x2, y2 = caixa
    if x2 - x1 <= 2 * margem_x or y2 - y1 <= 2 * margem_y:
        raise ValueError(f'Celula pequena demais: {caixa}')
    return imagem[y1 + margem_y:y2 - margem_y,
                  x1 + margem_x:x2 - margem_x].copy()


def preprocessar_tabela(resultado: dict) -> list[dict]:
    """Retorna uma entrada por linha, sem classificar presenca.

    Mantem os recortes RGB originais para conferencia humana.
    A preparacao foi ajustada para paginas renderizadas a 300 DPI.
    """
    imagem = resultado['imagem']
    x1, y1, x2, y2 = resultado['tabela']
    tabela = imagem[y1:y2, x1:x2]
    if tabela.size == 0 or not resultado['alunos']:
        raise ValueError('Tabela vazia.')

    cinza = cv2.cvtColor(tabela, cv2.COLOR_RGB2GRAY)
    # Canal mais escuro ajuda a manter tinta colorida, inclusive azul.
    tinta = np.min(tabela, axis=2).astype(np.uint8)
    nomes = _binarizar(_normalizar(cinza), 9)
    assinaturas = _binarizar(_normalizar(tinta), 7)

    # Linhas impressas atravessam boa parte da largura da tabela.
    # Detectar antes de recortar evita confundir traços curtos com a grade.
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT,
                                      (max(25, tabela.shape[1] // 4), 1))
    grade = cv2.morphologyEx(nomes, cv2.MORPH_OPEN, kernel)
    grade = cv2.dilate(grade, np.ones((3, 3), dtype=np.uint8))
    nomes = cv2.bitwise_and(nomes, cv2.bitwise_not(grade))
    assinaturas = cv2.bitwise_and(assinaturas, cv2.bitwise_not(grade))

    def relativa(caixa):
        a, b, c, d = caixa
        return a - x1, b - y1, c - x1, d - y1

    celulas = []
    for aluno in resultado['alunos']:
        nome = _recortar(nomes, relativa(aluno['nome']), 6, 3)
        assinatura = _recortar(assinaturas, relativa(aluno['assinatura']), 7, 3)
        # Fundo branco para leitura e visualizacao.
        nome = cv2.copyMakeBorder(255 - nome, 8, 8, 8, 8,
                                  cv2.BORDER_CONSTANT, value=255)
        celulas.append({
            'linha': aluno['linha'],
            'nome_original': _recortar(imagem, aluno['nome']),
            'assinatura_original': _recortar(imagem, aluno['assinatura']),
            'nome_tratado': nome,
            'assinatura_tratada': 255 - assinatura,
        })
    return celulas
