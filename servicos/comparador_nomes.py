"""Normalizacao conservadora; similaridade apenas sugere revisao."""
import unicodedata
import re
from difflib import SequenceMatcher


def normalizar_nome(nome: str) -> str:
    texto = unicodedata.normalize('NFKD', nome.upper())
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return ' '.join(texto.replace('’', "'").split())


def nome_valido(nome: str) -> bool:
    return bool(re.fullmatch(r"[A-Z]+(?:[ '\-][A-Z]+)+", nome))


def sugerir_nomes(nome: str, candidatos, limite: float = .88) -> list[str]:
    return sorted(c for c in set(candidatos) if c != nome and
                  SequenceMatcher(None, nome, c, autojunk=False).ratio() >= limite)
