from pathlib import Path
from datetime import datetime
from collections import Counter
import argparse
import csv
import hashlib
import re

from processamento.leitor_pdf import ler_pdf
from processamento.detector_tabela import detectar_tabela
from processamento.preprocessamento import preprocessar_tabela
from processamento.ocr import reconhecer_nomes
from processamento.detector_assinaturas import detectar_assinaturas
from servicos.frequencia import consolidar_frequencia

RAIZ = Path(__file__).resolve().parents[1]
ENTRADA = RAIZ / 'dados' / 'entrada'
SAIDA = RAIZ / 'dados' / 'saida' / 'frequencia'


def salvar_csv(caminho, registros, campos):
    with caminho.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=campos, delimiter=';')
        w.writeheader()
        # Evita interpretacao de texto extraido como formula no Excel.
        w.writerows({k: "'" + v if isinstance(v, str) and v.startswith(('=', '+', '-', '@', '\t', '\r')) else v
                     for k, v in r.items()} for r in registros)


def indexar(registros):
    index = {r['linha']: r for r in registros}
    if len(index) != len(registros):
        raise ValueError('Linhas repetidas no resultado de processamento.')
    return index


def main():
    parser = argparse.ArgumentParser(description='Teste integrado de uma turma por vez.')
    parser.add_argument('--turma', required=True)
    args = parser.parse_args()
    arquivos = sorted(ENTRADA.glob('*.pdf'))
    if not arquivos:
        raise SystemExit('Nenhum PDF encontrado em dados/entrada.')
    aulas, hashes, registros = set(), set(), []
    for arquivo in arquivos:
        # Nesta etapa, turma e data sao lidas do nome do arquivo, nao do cabecalho.
        m = re.fullmatch(re.escape(args.turma) + r'\s+(\d{2}\.\d{2}\.\d{4})(?:\s*\(\d+\))?', arquivo.stem, re.I)
        if not m:
            raise SystemExit(f'Arquivo fora do padrao da turma: {arquivo.name}')
        aula = datetime.strptime(m[1], '%d.%m.%Y').date().isoformat()
        digest = hashlib.sha256(arquivo.read_bytes()).hexdigest()
        if aula in aulas or digest in hashes:
            raise SystemExit(f'Possivel duplicidade ou mais de uma aula na data: {arquivo.name}')
        aulas.add(aula)
        hashes.add(digest)
        print(f'\nArquivo: {arquivo.name}', flush=True)
        imagens = ler_pdf(arquivo)
        if not imagens:
            raise ValueError('PDF sem paginas.')
        for pagina, imagem in enumerate(imagens, 1):
            celulas = preprocessar_tabela(detectar_tabela(imagem))
            nomes = indexar(reconhecer_nomes(celulas))
            assinaturas = indexar(detectar_assinaturas(celulas))
            linhas = indexar(celulas)
            if not linhas or nomes.keys() != linhas.keys() or assinaturas.keys() != linhas.keys():
                raise ValueError('Divergencia de linhas entre os modulos.')
            for linha in sorted(linhas):
                n, s = nomes[linha], assinaturas[linha]
                registros.append({'turma': args.turma, 'aula': aula, 'arquivo': arquivo.name,
                                  'pagina': pagina, 'linha': linha, 'numero_impresso': n['numero_impresso'],
                                  'nome': n['nome'], 'texto_ocr': n['texto_ocr'], 'confianca': n['confianca'],
                                  'revisao_ocr': n['revisao'], 'motivo_ocr': n['motivo'],
                                  'status': s['status'], 'motivo_assinatura': s['motivo']})
            print(f'Pagina {pagina}: {len(linhas)} registros integrados', flush=True)
    resultado = consolidar_frequencia(registros, sorted(aulas))
    SAIDA.mkdir(parents=True, exist_ok=True)
    salvar_csv(SAIDA / 'registros_por_aula.csv', registros, list(registros[0]))
    campos = list(resultado[0])
    salvar_csv(SAIDA / 'frequencia_consolidada.csv', resultado, campos)
    salvar_csv(SAIDA / 'alunos_100_confirmados.csv', [r for r in resultado if r['situacao'] == '100% CONFIRMADO'], campos)
    salvar_csv(SAIDA / 'alunos_100_preliminares.csv', [r for r in resultado if r['situacao'] == '100% PRELIMINAR'], campos)
    print(f'\nTOTAL: {len(registros)} registros | {len(resultado)} grupos de nomes | {len(aulas)} aulas')
    for status, n in sorted(Counter(r['situacao'] for r in resultado).items()):
        print(f'{status}: {n}')
    print('Conferencia financeira: NAO REALIZADA')
    print(f'Relatorios: {SAIDA}')

if __name__ == '__main__':
    main()
