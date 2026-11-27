from pathlib import Path

import numpy as np
import pymupdf


def ler_pdf(caminho: str | Path, dpi: int = 300) -> list[np.ndarray]:
    """Converte cada página do PDF em uma imagem RGB."""

    caminho = Path(caminho)

    if not caminho.is_file():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

    imagens = []

    with pymupdf.open(caminho) as documento:

        if documento.needs_pass:
            raise ValueError("PDF protegido por senha.")

        for pagina in documento:

            pix = pagina.get_pixmap(
                dpi=dpi,
                colorspace=pymupdf.csRGB,
                alpha=False
            )

            imagem = np.frombuffer(
                pix.samples,
                dtype=np.uint8
            )

            imagem = imagem.reshape(
                pix.height,
                pix.width,
                3
            ).copy()

            imagens.append(imagem)

    return imagens
