from pathlib import Path
from collections import Counter
import csv
from PIL import Image, ImageDraw
from processamento.leitor_pdf import ler_pdf
from processamento.detector_tabela import detectar_tabela
from processamento.preprocessamento import preprocessar_tabela
from processamento.detector_assinaturas import detectar_assinaturas

RAIZ = Path(__file__).resolve().parents[1]
ENTRADA = RAIZ / 'dados' / 'entrada'
SAIDA = RAIZ / 'dados' / 'saida' / 'assinaturas'
CORES = {'PRESENTE': '#16803d', 'FALTA': '#b91c1c', 'REVISAR': '#a16207'}


def salvar_comparacao(celulas, resultados, destino):
    painel = Image.new('RGB', (1150, 42 + 60*len(celulas)), 'white')
    d = ImageDraw.Draw(painel)
    for x, titulo in [(10, 'Linha / status'), (180, 'Assinatura original'), (665, 'Assinatura tratada')]:
        d.text((x, 12), titulo, fill='black')
    for i, (c, r) in enumerate(zip(celulas, resultados)):
        y = 42 + 60*i
        d.text((10, y+10), f"{r['linha']:02d} - {r['status']}", fill=CORES[r['status']])
        for x, campo in [(180, 'assinatura_original'), (665, 'assinatura_tratada')]:
            recorte = Image.fromarray(c[campo]).convert('RGB')
            recorte.thumbnail((470, 50), Image.Resampling.LANCZOS)
            painel.paste(recorte, (x, y+4))
        d.line((0, y+59, painel.width, y+59), fill='#dddddd')
    painel.save(destino)


def main():
    arquivos = sorted(ENTRADA.glob('*.pdf'))
    if not arquivos:
        print('Nenhum PDF encontrado em dados/entrada.')
        return
    SAIDA.mkdir(parents=True, exist_ok=True)
    registros, falhas = [], 0
    for arquivo in arquivos:
        print(f'\nArquivo: {arquivo.name}')
        try:
            for pagina, imagem in enumerate(ler_pdf(arquivo), 1):
                celulas = preprocessar_tabela(detectar_tabela(imagem))
                resultados = detectar_assinaturas(celulas)
                destino = SAIDA / f'{arquivo.stem}_pagina_{pagina}_assinaturas.png'
                salvar_comparacao(celulas, resultados, destino)
                for r in resultados:
                    print(f"Linha {r['linha']:02d} | {r['status']:8s} | {r['motivo']}")
                    registros.append({'arquivo': arquivo.name, 'pagina': pagina, **r})
                c = Counter(r['status'] for r in resultados)
                print(f"Pagina {pagina}: {c['PRESENTE']} presentes | {c['FALTA']} faltas | {c['REVISAR']} revisar")
                print(f'Comparacao: {destino.name}')
        except Exception as erro:
            falhas += 1
            print(f'Erro: {erro}')
    if registros:
        destino = SAIDA / 'resultado_assinaturas.csv'
        with destino.open('w', newline='', encoding='utf-8-sig') as f:
            escritor = csv.DictWriter(f, fieldnames=list(registros[0]), delimiter=';')
            escritor.writeheader()
            escritor.writerows(registros)
        c = Counter(r['status'] for r in registros)
        print(f"\nTOTAL: {len(registros)} linhas | {c['PRESENTE']} presentes | {c['FALTA']} faltas | {c['REVISAR']} revisar")
        print(f'Relatorio: {destino}')
    print(f'Arquivos com erro: {falhas}')
    if falhas:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
