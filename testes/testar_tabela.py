from pathlib import Path

import cv2
from PIL import Image

from processamento.leitor_pdf import ler_pdf
from processamento.detector_tabela import detectar_tabela

RAIZ = Path(__file__).resolve().parents[1]
ENTRADA = RAIZ / 'dados' / 'entrada'
SAIDA = RAIZ / 'dados' / 'saida' / 'tabelas'


def main():
    SAIDA.mkdir(parents=True, exist_ok=True)
    arquivos = sorted(ENTRADA.glob('*.pdf'))
    if not arquivos:
        print('Nenhum PDF encontrado em dados/entrada.')
        return
    for arquivo in arquivos:
        print(f'\nArquivo: {arquivo.name}')
        try:
            for numero, imagem in enumerate(ler_pdf(arquivo), 1):
                resultado = detectar_tabela(imagem)
                visual = resultado['imagem'].copy()
                for aluno in resultado['alunos']:
                    for campo, cor in [('nome', (30, 100, 255)),
                                       ('assinatura', (20, 170, 60))]:
                        x1, y1, x2, y2 = aluno[campo]
                        cv2.rectangle(visual, (x1, y1), (x2, y2), cor, 3)
                destino = SAIDA / f'{arquivo.stem}_pagina_{numero}_tabela.png'
                Image.fromarray(visual).save(destino)
                print(f'Pagina {numero}: {len(resultado["alunos"])} linhas de alunos')
                print(f'Imagem salva: {destino.name}')
        except Exception as erro:
            print(f'Erro: {erro}')


if __name__ == '__main__':
    main()
