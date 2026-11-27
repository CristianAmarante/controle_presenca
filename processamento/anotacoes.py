"""Anotacoes com PaddleOCR. Similaridade gera suspeita, nunca confirmacao."""
import re
import unicodedata
import cv2
from rapidfuzz.distance import Levenshtein
from processamento.ocr_paddle import testar_anotacoes, ler_recortes

TERMOS = {'TRANCOU', 'TRANCADO', 'TRANCADA', 'MATRICULA TRANCADA'}


def normalizar(texto):
    texto = unicodedata.normalize('NFKD', str(texto).upper())
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return ' '.join(texto.strip(' .,;:!?').split())


def palavra_trancamento(texto, confianca):
    return normalizar(texto) in TERMOS and confianca >= 80


def suspeita(texto, confianca):
    t = normalizar(texto)
    if confianca < 60 or not re.fullmatch(r'[A-Z ]+', t):
        return False
    if t in TERMOS:
        return True
    # Nao procura substrings e nao usa palavras muito curtas.
    if not 6 <= len(t) <= 9 or ' ' in t:
        return False
    return Levenshtein.distance(t, 'TRANCOU') <= 2


def classificar_anotacao(texto, confianca, texto2='', confianca2=0):
    confirmado = (palavra_trancamento(texto, confianca)
                  and palavra_trancamento(texto2, confianca2))
    possivel = not confirmado and (suspeita(texto, confianca) or suspeita(texto2, confianca2))
    return {'trancamento_detectado': confirmado, 'suspeita_trancamento': possivel,
            'texto_anotacao': ' | '.join(filter(None, [texto, texto2])),
            'confianca_anotacao': confianca,
            'confianca_anotacao_tratada': confianca2}


def detectar_anotacoes(celulas, modelo=None):
    """Le todas as celulas; segunda leitura somente para termo exato forte."""
    primeiras = testar_anotacoes(celulas, modelo)
    if [c['linha'] for c in celulas] != [r['linha'] for r in primeiras]:
        raise ValueError('Linhas de anotacoes divergentes.')
    segundas = {}
    indices, imagens = [], []
    for i, (c, r) in enumerate(zip(celulas, primeiras)):
        if palavra_trancamento(r['texto'], r['confianca']):
            img = c['assinatura_tratada']
            if img.size:
                img = cv2.copyMakeBorder(img, 8, 8, 8, 8, cv2.BORDER_CONSTANT, value=255)
                if img.ndim == 2:
                    img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                else:
                    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                indices.append(i)
                imagens.append(img)
    segundas.update(zip(indices, ler_recortes(imagens, modelo)))
    return [{'linha': r['linha'], **classificar_anotacao(r['texto'], r['confianca'], *segundas.get(i, ('', 0)))}
            for i, r in enumerate(primeiras)]
