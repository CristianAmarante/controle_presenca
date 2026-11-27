from pathlib import Path
import csv

from processamento.leitor_pdf import ler_pdf
from processamento.detector_tabela import detectar_tabela
from processamento.preprocessamento import preprocessar_tabela
from processamento.ocr import reconhecer_nomes

RAIZ = Path(__file__).resolve().parents[1]
ENTRADA = RAIZ / 'dados' / 'entrada'
SAIDA = RAIZ / 'dados' / 'saida' / 'ocr'


def main():
    arquivos = sorted(ENTRADA.glob('*.pdf'))
    if not arquivos:
        print('Nenhum PDF encontrado em dados/entrada.')
        return
    SAIDA.mkdir(parents=True, exist_ok=True)
    registros = []
    falhas = 0
    for arquivo in arquivos:
        print(f'\nArquivo: {arquivo.name}')
        try:
            for pagina, imagem in enumerate(ler_pdf(arquivo), 1):
                celulas = preprocessar_tabela(detectar_tabela(imagem))
                leituras = reconhecer_nomes(celulas)
                for r in leituras:
                    status = 'REVISAR' if r['revisao'] else 'LEITURA OK'
                    print(f"Linha {r['linha']:02d} | Nº {r['numero_impresso']} | "
                          f"{r['nome']} | {r['confianca']:.1f} | {status}")
                    registros.append({'arquivo': arquivo.name, 'pagina': pagina, **r})
                print(f'Pagina {pagina}: {len(leituras)} linhas; '
                      f'{sum(r["revisao"] for r in leituras)} para revisao')
        except Exception as erro:
            falhas += 1
            print(f'Erro: {erro}')
    if registros:
        destino = SAIDA / 'resultado_ocr.csv'
        with destino.open('w', encoding='utf-8-sig', newline='') as f:
            escritor = csv.DictWriter(f, fieldnames=list(registros[0]), delimiter=';')
            escritor.writeheader()
            escritor.writerows(registros)
        print(f'\nRelatorio: {destino}')
    print(f'Linhas processadas: {len(registros)} | Arquivos com erro: {falhas}')
    if falhas:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
