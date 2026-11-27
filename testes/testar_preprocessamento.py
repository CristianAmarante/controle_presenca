from pathlib import Path

from PIL import Image, ImageDraw

from processamento.leitor_pdf import ler_pdf
from processamento.detector_tabela import detectar_tabela
from processamento.preprocessamento import preprocessar_tabela

RAIZ = Path(__file__).resolve().parents[1]
ENTRADA = RAIZ / 'dados' / 'entrada'
SAIDA = RAIZ / 'dados' / 'saida' / 'preprocessamento'


def salvar_comparacao(celulas, destino):
    campos = ('nome_original', 'nome_tratado',
              'assinatura_original', 'assinatura_tratada')
    titulos = ('Nome original', 'Nome tratado',
               'Assinatura original', 'Assinatura tratada')
    largura, altura = 440, 42
    painel = Image.new('RGB', (70 + largura * 4, 36 + altura * len(celulas)), 'white')
    desenho = ImageDraw.Draw(painel)
    desenho.text((6, 10), 'Linha', fill='black')
    for j, titulo in enumerate(titulos):
        desenho.text((70 + j * largura, 10), titulo, fill='black')
    for i, celula in enumerate(celulas):
        y = 36 + i * altura
        desenho.text((6, y + 10), str(celula['linha']), fill='black')
        for j, campo in enumerate(campos):
            recorte = Image.fromarray(celula[campo]).convert('RGB')
            recorte.thumbnail((largura - 8, altura - 6), Image.Resampling.LANCZOS)
            painel.paste(recorte, (70 + j * largura, y + 2))
        desenho.line((0, y + altura - 1, painel.width, y + altura - 1), fill='#dddddd')
    painel.save(destino)


def main():
    SAIDA.mkdir(parents=True, exist_ok=True)
    arquivos = sorted(ENTRADA.glob('*.pdf'))
    if not arquivos:
        print('Nenhum PDF encontrado em dados/entrada.')
        return
    for arquivo in arquivos:
        print(f'\nArquivo: {arquivo.name}')
        try:
            for pagina, imagem in enumerate(ler_pdf(arquivo), 1):
                celulas = preprocessar_tabela(detectar_tabela(imagem))
                pasta = SAIDA / f'{arquivo.stem}_pagina_{pagina}'
                pasta.mkdir(parents=True, exist_ok=True)
                for celula in celulas:
                    numero = celula['linha']
                    for campo in ('nome_original', 'nome_tratado',
                                  'assinatura_original', 'assinatura_tratada'):
                        Image.fromarray(celula[campo]).save(pasta / f'{numero:03d}_{campo}.png')
                salvar_comparacao(celulas, pasta / 'comparacao.png')
                print(f'Pagina {pagina}: {len(celulas)} nomes preparados')
                print(f'Pagina {pagina}: {len(celulas)} assinaturas preparadas')
                print(f'Comparacao: {pasta.name}/comparacao.png')
        except Exception as erro:
            print(f'Erro: {erro}')


if __name__ == '__main__':
    main()
