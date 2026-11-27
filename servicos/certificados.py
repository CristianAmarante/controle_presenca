"""Certificados Aluno Nota 10, em memória, a partir da seleção final da V4."""
from datetime import date
from io import BytesIO
from pathlib import Path
import re
import os
import unicodedata
from zipfile import ZipFile, ZIP_DEFLATED

from PIL import Image, ImageOps
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth, registerFont, registerTypeFace, Font, EmbeddedType1Face
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

TEMPLATE = Path(__file__).resolve().parents[1] / 'templates' / 'certificado_nota10.jpg'
MESES = ('janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho',
         'agosto', 'setembro', 'outubro', 'novembro', 'dezembro')


def periodo_certificado(aulas):
    """Usa a data mais recente, não o relógio do computador."""
    datas = [date.fromisoformat(a) for a in aulas]
    if not datas:
        raise ValueError('Nenhuma aula informada.')
    ultima = max(datas)
    return MESES[ultima.month - 1], ultima.year


def _fundo(template):
    # Preserva toda a arte, removendo apenas os dois campos variáveis.
    with Image.open(template) as arquivo:
        img = ImageOps.exif_transpose(arquivo).convert('RGB')
    if img.size != (1600, 1131):
        raise ValueError('O template deve ser a imagem original de 1600 x 1131 pixels.')
    px = img.load()
    # Remove ALUNO e a primeira linha do texto (incluindo o sublinhado).
    for x0, y0, x1, y1 in ((710, 553, 890, 608), (140, 645, 1450, 695)):
        for x in range(x0, x1):
            cima, baixo = px[x, y0-1], px[x, y1]
            for y in range(y0, y1):
                t = (y-y0+1)/(y1-y0+1)
                px[x,y] = tuple(round(a*(1-t)+b*t) for a,b in zip(cima,baixo))
    return img


def _fonte_frase():
    """Prefere uma fonte geométrica local; não exige arquivos extras."""
    windows = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts'
    configurada = os.environ.get('CERTIFICADO_FONTE_REGULAR')
    caminhos = ([Path(configurada)] if configurada else []) + [
        windows / 'GOTHIC.TTF', windows / 'gothic.ttf',
    ]
    for caminho in caminhos:
        if caminho.is_file():
            try:
                registerFont(TTFont('CertificadoRegular', str(caminho)))
                return 'CertificadoRegular'
            except Exception:
                continue
    # Equivalente geométrico disponível em algumas instalações Linux.
    afm = Path('/usr/share/fonts/type1/urw-base35/URWGothic-Book.afm')
    pfb = Path('/usr/share/fonts/X11/Type1/URWGothic-Book.pfb')
    if afm.is_file() and pfb.is_file():
        try:
            face = EmbeddedType1Face(str(afm), str(pfb))
            registerTypeFace(face)
            registerFont(Font('CertificadoGeometrica', face.name, 'WinAnsiEncoding'))
            return 'CertificadoGeometrica'
        except Exception:
            pass
    return 'Helvetica'


def _nome(nome):
    if not isinstance(nome,str):
        raise ValueError('Nome inválido para certificado.')
    nome = ' '.join(unicodedata.normalize('NFC', nome).split()).upper()
    if not nome or not any(c.isalpha() for c in nome):
        raise ValueError('Nome inválido para certificado.')
    # Fontes padrão do PDF cobrem nomes em português (WinAnsi).
    try:
        nome.encode('cp1252')
    except UnicodeEncodeError as e:
        raise ValueError('Nome contém caracteres não suportados pela fonte do certificado.') from e
    return nome


def _pdf(nome, mes, fundo, demonstracao=False):
    largura, altura = landscape(A4)
    sx, sy = largura/1600, altura/1131
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(largura,altura))
    c.setTitle('Certificado Aluno Nota 10' if not demonstracao else 'Demonstração sem validade')
    c.drawImage(fundo, 0, 0, largura, altura)
    c.setFillColorRGB(0,0,0)
    def central(texto, fonte, tamanho_px, largura_px, x, baseline):
        tamanho = tamanho_px*sy
        medido = stringWidth(texto,fonte,tamanho)
        if medido > largura_px*sx:
            tamanho *= largura_px*sx/medido
        if tamanho < 10:
            raise ValueError('Texto longo demais para o espaço disponível no certificado.')
        c.setFont(fonte,tamanho)
        c.drawCentredString(x*sx,altura-baseline*sy,texto)
    central(nome,'Helvetica-Bold',40,1280,800,592)
    frase = f'Em reconhecimento ao seu destaque como Aluno Nota 10 do mês de {mes},'
    central(frase,_fonte_frase(),35,1300,800,678)
    if demonstracao:
        c.setFillColorRGB(0.65,0.12,0.12)
        c.setFont('Helvetica-Bold',15)
        c.drawCentredString(largura/2,altura-442*sy,'DEMONSTRAÇÃO — SEM VALIDADE')
    c.showPage(); c.save()
    return buf.getvalue()


def _arquivo_nome(nome):
    base = unicodedata.normalize('NFKD', nome).encode('ascii','ignore').decode()
    return re.sub(r'[^A-Z0-9]+','_',base.upper()).strip('_')[:120] or 'ALUNO'


def gerar_certificados(resultado, aulas, template=TEMPLATE):
    """Retorna mês, ano, PDFs individuais e ZIP. Só emite para selecionado=True.

    Não recalcula elegibilidade nem grava dados pessoais no disco.
    """
    mes, ano = periodo_certificado(aulas)
    selecionados = [r for r in resultado if r.get('selecionado') is True]
    if not selecionados:
        return {'mes':mes, 'ano':ano, 'arquivos':[], 'zip':None}
    fundo = ImageReader(_fundo(template))
    arquivos, usados = [], set()
    for r in selecionados:
        nome = _nome(r['nome'])
        base = f'{_arquivo_nome(nome)}_{mes.upper()}_{ano}'
        arquivo, i = base+'.pdf', 2
        while arquivo in usados:
            arquivo = f'{base}_{i}.pdf'; i += 1
        usados.add(arquivo)
        arquivos.append({'nome':nome, 'arquivo':arquivo, 'pdf':_pdf(nome,mes,fundo)})
    buf=BytesIO()
    with ZipFile(buf,'w',ZIP_DEFLATED) as z:
        for item in arquivos:
            z.writestr(item['arquivo'],item['pdf'])
    return {'mes':mes,'ano':ano,'arquivos':arquivos,'zip':buf.getvalue()}
