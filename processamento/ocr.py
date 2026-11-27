"""OCR local de nomes impressos; nao interpreta assinaturas."""
import os
import re
import shutil
from pathlib import Path

import cv2
import numpy as np
import pytesseract


def configurar_ocr():
    caminho = os.environ.get('TESSERACT_CMD') or shutil.which('tesseract')
    if not caminho:
        padrao = Path(os.environ.get('ProgramFiles', r'C:\Program Files')) / 'Tesseract-OCR' / 'tesseract.exe'
        if padrao.is_file():
            caminho = str(padrao)
    if not caminho:
        raise RuntimeError('Tesseract nao encontrado. Instale o programa ou defina TESSERACT_CMD.')
    pytesseract.pytesseract.tesseract_cmd = caminho
    if 'por' not in pytesseract.get_languages(config=''):
        raise RuntimeError('Idioma por ausente. Instale por.traineddata no diretorio tessdata.')


def _interpretar(celula, palavras, limite):
    palavras.sort(key=lambda p: p[0])
    texto = ' '.join(p[1] for p in palavras).strip()
    confianca = round(min((p[2] for p in palavras), default=0), 2)
    # O numero impresso pode ser diferente do indice fisico da linha.
    match = re.match(r'^\s*(\d+)\s*[-–—.:]?\s*(.*)$', texto)
    numero = int(match.group(1)) if match else None
    nome_bruto = (match.group(2) if match else texto).strip().upper()
    # Retira somente pontuacao isolada nas extremidades; preserva texto OCR.
    nome = nome_bruto.strip(" ,.:;!?\"'’“”–—-")
    motivos = []
    if nome != nome_bruto:
        motivos.append('pontuacao externa removida; conferir')
    if numero is None:
        motivos.append('numero nao identificado')
    if len(nome.split()) < 2 or not all(c.isalpha() or c in " -'’" for c in nome):
        motivos.append('nome incompleto ou caracteres inesperados')
    if confianca < limite:
        motivos.append('baixa confianca')
    return {'linha': celula['linha'], 'numero_impresso': numero,
            'nome': nome, 'texto_ocr': texto, 'confianca': confianca,
            'revisao': bool(motivos), 'motivo': '; '.join(motivos)}


def reconhecer_nomes(celulas: list[dict], limite: float = 80) -> list[dict]:
    """Recebe preprocessar_tabela(); devolve uma leitura por celula.

    Agrupa recortes em uma imagem com separacao vertical para executar
    o OCR em lote. Confianca = menor nota das palavras, nao probabilidade.
    """
    if not celulas:
        return []
    if not 0 <= limite <= 100:
        raise ValueError('Limite deve estar entre 0 e 100.')
    configurar_ocr()
    recortes = []
    for celula in celulas:
        img = celula['nome_tratado']
        if img.ndim != 2 or img.size == 0:
            raise ValueError('Recorte de nome invalido.')
        # Remove excesso de margem em branco, sem cortar a tinta.
        pontos = cv2.findNonZero(255 - img)
        if pontos is not None:
            x, y, w, h = cv2.boundingRect(pontos)
            img = img[y:y+h, x:x+w]
        recortes.append(img)
    altura = max(i.shape[0] for i in recortes) + 32
    largura = max(i.shape[1] for i in recortes) + 32
    painel = np.full((altura * len(recortes), largura), 255, np.uint8)
    for n, img in enumerate(recortes):
        h, w = img.shape
        y = n * altura + (altura - h) // 2
        painel[y:y+h, 16:16+w] = img
    dados = pytesseract.image_to_data(painel, lang='por',
             config='--oem 1 --psm 6 --dpi 300',
             output_type=pytesseract.Output.DICT, timeout=90)
    grupos = [[] for _ in recortes]
    for j, palavra in enumerate(dados['text']):
        palavra = palavra.strip()
        conf = float(dados['conf'][j])
        if not palavra or conf < 0:
            continue
        centro = dados['top'][j] + dados['height'][j] / 2
        n = int(centro // altura)
        if 0 <= n < len(grupos):
            grupos[n].append((dados['left'][j], palavra, conf))
    resultados = [_interpretar(c, p, limite) for c, p in zip(celulas, grupos)]
    # Numeracao repetida ou regressiva na mesma ficha indica possivel falha.
    for anterior, atual in zip(resultados, resultados[1:]):
        a, b = anterior['numero_impresso'], atual['numero_impresso']
        if a is not None and b is not None and b <= a:
            for r in (anterior, atual):
                r['revisao'] = True
                r['motivo'] = '; '.join(filter(None, [r['motivo'], 'numeracao nao crescente']))
    return resultados
