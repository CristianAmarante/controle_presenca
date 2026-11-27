"""OCR experimental PP-OCRv6 Medium, compativel com as celulas existentes."""
from functools import lru_cache
import math
import re
import cv2
import numpy as np

MODELO = 'PP-OCRv6_medium_rec'


@lru_cache(maxsize=1)
def obter_modelo():
    from paddleocr import TextRecognition
    return TextRecognition(model_name=MODELO, device='cpu',
                           engine='paddle_static')


def _bgr(img):
    if img.size == 0:
        raise ValueError('Recorte vazio.')
    if img.ndim == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    if img.ndim == 3 and img.shape[2] == 3:
        return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    raise ValueError('Formato de imagem inesperado.')


def preparar_nome(celula, variante):
    if variante == 'tratado':
        img = celula['nome_tratado']
        pontos = cv2.findNonZero((img < 180).astype(np.uint8))
        if pontos is not None:
            x, y, w, h = cv2.boundingRect(pontos)
            img = img[y:y+h, x:x+w]
    elif variante == 'original':
        img = celula['nome_original']
        # Exclui a grade nas bordas, preservando a numeracao impressa.
        h, w = img.shape[:2]
        if h > 14 and w > 20:
            img = img[4:-4, 5:-5]
        # Remove apenas o excesso de espaco lateral usando contraste local.
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        fundo = cv2.GaussianBlur(gray, (0, 0), 12)
        contraste = cv2.subtract(fundo, gray)
        pontos = cv2.findNonZero((contraste > 22).astype(np.uint8))
        if pontos is not None:
            x, _, w, _ = cv2.boundingRect(pontos)
            img = img[:, max(0, x-6):min(img.shape[1], x+w+6)]
    else:
        raise ValueError('Variante deve ser original ou tratado.')
    return cv2.copyMakeBorder(_bgr(img), 8, 8, 8, 8,
                              cv2.BORDER_CONSTANT, value=(255,255,255))


def ler_recortes(imagens, modelo=None):
    if not imagens:
        return []
    modelo = modelo if modelo is not None else obter_modelo()
    resultados = list(modelo.predict(input=imagens, batch_size=4))
    if len(resultados) != len(imagens):
        raise RuntimeError('Quantidade de resultados diferente dos recortes.')
    leituras = []
    for r in resultados:
        # Result do PaddleX e um mapeamento; json pode ter chave res.
        if 'rec_text' not in r:
            r = r.json['res'] if hasattr(r, 'json') else r['res']
        texto = str(r['rec_text']).strip()
        nota = float(r['rec_score'])
        if not math.isfinite(nota) or not 0 <= nota <= 1:
            raise ValueError('Pontuacao PaddleOCR invalida.')
        leituras.append((texto, round(nota*100, 2)))
    return leituras


def interpretar(linha, texto, confianca, limite=80):
    m = re.match(r'^\s*(\d+)\s*[-–—.:]?\s*(.*)$', texto)
    numero = int(m[1]) if m else None
    bruto = (m[2] if m else texto).strip().upper()
    nome = bruto.strip(" ,.:;!?\"'’“”–—-")
    motivos = []
    if numero is None or numero <= 0:
        motivos.append('numero nao identificado ou invalido')
    if bruto != nome:
        motivos.append('pontuacao externa removida')
    if len(nome.split()) < 2 or not all(c.isalpha() or c in " -'’" for c in nome):
        motivos.append('nome incompleto ou caracteres inesperados')
    if confianca < limite:
        motivos.append('baixa confianca')
    return dict(linha=linha, numero_impresso=numero, nome=nome,
                texto_ocr=texto, confianca=confianca, revisao=bool(motivos),
                motivo='; '.join(motivos))


def reconhecer_nomes(celulas, limite=80, variante='original', modelo=None):
    if not 0 <= limite <= 100:
        raise ValueError('Limite deve estar entre 0 e 100.')
    leituras = ler_recortes([preparar_nome(c, variante) for c in celulas], modelo)
    registros = [interpretar(c['linha'], t, s, limite) for c,(t,s) in zip(celulas,leituras)]
    for a,b in zip(registros,registros[1:]):
        if a['numero_impresso'] is not None and b['numero_impresso'] is not None and b['numero_impresso'] <= a['numero_impresso']:
            for r in (a,b):
                r['revisao'] = True
                r['motivo'] = '; '.join(filter(None,[r['motivo'],'numeracao nao crescente']))
    return registros


def testar_anotacoes(celulas, modelo=None):
    """Somente diagnostico: nao altera presenca nem confirma trancamento."""
    imagens = []
    for c in celulas:
        img = c['assinatura_original']
        if img.shape[0] > 12 and img.shape[1] > 20:
            img = img[4:-4, 6:-6]
        imagens.append(_bgr(img))
    resultados = ler_recortes(imagens, modelo)
    return [{'linha': c['linha'], 'texto': t, 'confianca': s}
            for c,(t,s) in zip(celulas,resultados)]
