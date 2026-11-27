"""Integra os modulos existentes, sem gravar relatorios automaticamente."""
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import re

from processamento.leitor_pdf import ler_pdf
from processamento.detector_tabela import detectar_tabela
from processamento.preprocessamento import preprocessar_tabela
from processamento.ocr_paddle import reconhecer_nomes
from processamento.detector_assinaturas import detectar_assinaturas
from processamento.anotacoes import detectar_anotacoes


def identificar_aula(nome, turma):
    m = re.fullmatch(re.escape(turma) + r'\s+(\d{2}\.\d{2}\.\d{4})(?:\s*\(\d+\))?', Path(nome).stem, re.I)
    if not m or Path(nome).suffix.lower() != '.pdf':
        raise ValueError(f'Nome fora do padrao da turma: {nome}')
    return datetime.strptime(m[1], '%d.%m.%Y').date().isoformat()


def _indexar(items):
    d = {r['linha']: r for r in items}
    if len(d) != len(items):
        raise ValueError('Linhas duplicadas no processamento.')
    return d


def processar_presencas(arquivos, turma, progresso=None):
    """arquivos: lista de pares (nome, bytes). Retorna registros, aulas, recortes."""
    if not arquivos or not turma.strip():
        raise ValueError('Informe a turma e pelo menos um PDF.')
    aulas, hashes, registros, recortes = set(), set(), [], {}
    entradas = []
    for nome, dados in arquivos:
        aula = identificar_aula(nome, turma.strip())
        digest = hashlib.sha256(dados).hexdigest()
        if aula in aulas or digest in hashes:
            raise ValueError(f'Possivel duplicidade ou duas aulas no mesmo dia: {nome}')
        aulas.add(aula)
        hashes.add(digest)
        entradas.append((nome, dados, aula))
    with TemporaryDirectory(prefix='presenca_') as pasta:
        for i, (nome, dados, aula) in enumerate(entradas, 1):
            caminho = Path(pasta) / f'{i}.pdf'
            caminho.write_bytes(dados)
            imagens = ler_pdf(caminho)
            if not imagens:
                raise ValueError(f'PDF sem paginas: {nome}')
            for pagina, imagem in enumerate(imagens, 1):
                celulas = preprocessar_tabela(detectar_tabela(imagem))
                nomes = _indexar(reconhecer_nomes(celulas))
                assinaturas = _indexar(detectar_assinaturas(celulas))
                anotacoes = _indexar(detectar_anotacoes(celulas))
                linhas = _indexar(celulas)
                if not linhas or nomes.keys() != linhas.keys() or assinaturas.keys() != linhas.keys() or anotacoes.keys() != linhas.keys():
                    raise ValueError(f'Divergencia de linhas: {nome}, pagina {pagina}')
                for linha in sorted(linhas):
                    n, s, c = nomes[linha], assinaturas[linha], linhas[linha]
                    chave = f'{aula}:{pagina}:{linha}'
                    registros.append({'id_registro': chave, 'turma': turma, 'aula': aula,
                        'arquivo': nome, 'pagina': pagina, 'linha': linha,
                        'numero_impresso': n['numero_impresso'], 'nome': n['nome'],
                        'texto_ocr': n['texto_ocr'], 'confianca': n['confianca'],
                        'revisao_ocr': n['revisao'], 'motivo_ocr': n['motivo'],
                        'status': s['status'], 'motivo_assinatura': s['motivo'],
                        'revisao_humana': False, **{k: v for k, v in anotacoes[linha].items() if k != 'linha'}})
                    recortes[chave] = {k: c[k] for k in ('nome_original', 'assinatura_original', 'assinatura_tratada')}
            if progresso:
                progresso(i, len(entradas))
    return registros, sorted(aulas), recortes
