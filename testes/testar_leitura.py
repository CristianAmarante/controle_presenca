from pathlib import Path
from PIL import Image
from processamento.leitor_pdf import ler_pdf


RAIZ = Path(__file__).resolve().parents[1]

ENTRADA = RAIZ / "dados" / "entrada"
SAIDA = RAIZ / "dados" / "saida" / "paginas"


def main():

    SAIDA.mkdir(parents=True, exist_ok=True)

    arquivos = sorted(ENTRADA.glob("*.pdf"))

    if not arquivos:
        print("Nenhum PDF encontrado em dados/entrada.")
        return

    for arquivo in arquivos:

        print(f"\nArquivo: {arquivo.name}")

        try:

            imagens = ler_pdf(arquivo)

            print(f"Páginas: {len(imagens)}")

            for numero, imagem in enumerate(imagens, start=1):

                destino = SAIDA / (
                    f"{arquivo.stem}_pagina_{numero}.png"
                )

                Image.fromarray(imagem).save(destino)

                altura, largura = imagem.shape[:2]

                print(f"Página {numero}: {largura} x {altura} pixels")
                print(f"Imagem salva: {destino.name}")

        except Exception as erro:

            print(f"Erro ao processar: {erro}")


if __name__ == "__main__":
    main()
