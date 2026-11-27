"""Comparacao local de OCR. Nao altera os resultados do aplicativo."""
import argparse
import csv
from pathlib import Path
from time import perf_counter
import unicodedata

from processamento.leitor_pdf import ler_pdf
from processamento.detector_tabela import detectar_tabela
from processamento.preprocessamento import preprocessar_tabela
from processamento.ocr import reconhecer_nomes as tesseract
from processamento.ocr_paddle import obter_modelo, reconhecer_nomes as paddle, testar_anotacoes

RAIZ = Path(__file__).resolve().parents[1]


def normalizar(s):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', s.upper())
                            if not unicodedata.combining(c)).split())


def gravar(path, rows):
    if rows:
        with path.open('w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter=';')
            w.writeheader(); w.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--anotacoes', action='store_true', help='Testa texto manuscrito sem alterar classificacoes')
    args = parser.parse_args()
    arquivos = sorted((RAIZ/'dados'/'entrada').glob('*.pdf'))
    if not arquivos:
        raise SystemExit('Nenhum PDF em dados/entrada.')
    saida = RAIZ/'dados'/'saida'/'comparacao_ocr'
    saida.mkdir(parents=True, exist_ok=True)
    print('Carregando PP-OCRv6 Medium (primeira execucao pode baixar o modelo)...', flush=True)
    t = perf_counter(); modelo = obter_modelo()
    print(f'Inicializacao do modelo: {perf_counter()-t:.2f} s', flush=True)
    tempos = dict(tesseract=0., paddle_original=0., paddle_tratado=0.)
    alertas = dict.fromkeys(tempos, 0)
    rows, anotacoes = [], []
    for arq in arquivos:
        print(f'\nArquivo: {arq.name}', flush=True)
        for pg, img in enumerate(ler_pdf(arq),1):
            celulas = preprocessar_tabela(detectar_tabela(img))
            leituras = {}
            for motor, f in [('tesseract', lambda: tesseract(celulas)),
                             ('paddle_original', lambda: paddle(celulas, variante='original', modelo=modelo)),
                             ('paddle_tratado', lambda: paddle(celulas, variante='tratado', modelo=modelo))]:
                t = perf_counter(); valores = f(); tempos[motor] += perf_counter()-t
                if [r['linha'] for r in valores] != [c['linha'] for c in celulas]:
                    raise RuntimeError(f'Linhas divergentes: {motor}, {arq.name}, pagina {pg}')
                alertas[motor] += sum(r['revisao'] for r in valores)
                leituras[motor] = valores
            for i, c in enumerate(celulas):
                r = {'arquivo': arq.name, 'pagina': pg, 'linha': c['linha']}
                for motor, registros in leituras.items():
                    for k,v in registros[i].items():
                        if k != 'linha': r[f'{motor}_{k}'] = v
                a,b,d = [leituras[m][i] for m in tempos]
                r['nomes_concordam'] = bool(a['nome']) and len({normalizar(x['nome']) for x in (a,b,d)}) == 1
                r['numeros_concordam'] = a['numero_impresso'] is not None and a['numero_impresso']==b['numero_impresso']==d['numero_impresso']
                rows.append(r)
            if args.anotacoes:
                for r in testar_anotacoes(celulas,modelo):
                    anotacoes.append({'arquivo':arq.name,'pagina':pg,**r})
            print(f'Pagina {pg}: {len(celulas)} linhas processadas',flush=True)
    gravar(saida/'comparacao_nomes.csv', rows)
    if args.anotacoes: gravar(saida/'anotacoes_experimentais.csv', anotacoes)
    print(f'\nTOTAL: {len(rows)} linhas')
    for m in tempos: print(f'{m}: {alertas[m]} alertas | {tempos[m]:.2f} s (OCR, sem carga inicial)')
    print(f'Nomes iguais entre os tres resultados: {sum(r["nomes_concordam"] for r in rows)}')
    print(f'Numeracao igual entre os tres resultados: {sum(r["numeros_concordam"] for r in rows)}')
    print('Concordancia nao mede precisao. Notas de confianca nao sao equivalentes entre motores.')
    print(f'Relatorios: {saida}')

if __name__ == '__main__': main()
