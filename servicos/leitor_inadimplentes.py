"""Importacao local do relatorio Educacional Web (.xls)."""
from pathlib import Path
import re
from servicos.comparador_nomes import normalizar_nome, nome_valido


def extrair_registros(linhas):
    """Valida cabecalho, registros e total. Nao retorna telefones."""
    cabecalho = None
    registros = []
    total = None
    matriculas = set()
    nomes = set()
    for numero, linha in enumerate(linhas, 1):
        valores = [str(v).strip() if v is not None else '' for v in linha]
        campos = [normalizar_nome(v).upper() for v in valores]
        if cabecalho is None:
            if 'ALUNO' in campos and 'Nº MATRICULA' in campos and 'Nº PARCELAS' in campos:
                cabecalho = tuple(campos.index(k) for k in ('ALUNO', 'Nº MATRICULA', 'Nº PARCELAS'))
            # NFKD transforma o indicador ordinal em O.
            elif 'ALUNO' in campos and 'NO MATRICULA' in campos and 'NO PARCELAS' in campos:
                cabecalho = tuple(campos.index(k) for k in ('ALUNO', 'NO MATRICULA', 'NO PARCELAS'))
            continue
        if not any(valores):
            continue
        if total is not None:
            raise ValueError('Conteudo inesperado apos a totalizacao.')
        rodapes = [re.fullmatch(r'TOTAL DE REGISTROS\s*:\s*(\d+)', c) for c in campos]
        rodape = next((m for m in rodapes if m), None)
        if rodape:
            total = int(rodape.group(1))
            continue
        if max(cabecalho) >= len(valores):
            raise ValueError(f'Linha {numero}: registro incompleto.')
        nome, matricula, parcelas = (valores[i] for i in cabecalho)
        chave = normalizar_nome(nome)
        if not nome_valido(chave) or not matricula:
            raise ValueError(f'Linha {numero}: nome ou matricula invalido.')
        try:
            quantidade = float(parcelas.replace(',', '.'))
            if quantidade < 1 or not quantidade.is_integer():
                raise ValueError
        except (ValueError, OverflowError):
            raise ValueError(f'Linha {numero}: quantidade de parcelas invalida.') from None
        if matricula in matriculas or chave in nomes:
            raise ValueError(f'Linha {numero}: possivel duplicidade ou homonimo; confira a lista.')
        matriculas.add(matricula)
        nomes.add(chave)
        registros.append({'nome': nome, 'matricula': matricula, 'parcelas': int(quantidade)})
    if cabecalho is None or total is None or total != len(registros):
        raise ValueError('Cabecalho ou totalizacao nao conferem. Lista nao validada.')
    return registros


def ler_inadimplentes(caminho):
    """Le .xls real usando xlrd. Falhas nunca viram lista vazia."""
    import xlrd
    caminho = Path(caminho)
    if caminho.suffix.lower() != '.xls':
        raise ValueError('Formato ainda nao suportado: envie o relatorio .xls.')
    livro = xlrd.open_workbook(str(caminho), on_demand=True)
    try:
        if livro.nsheets != 1:
            raise ValueError('Esperada uma unica aba; confira o formato do relatorio.')
        aba = livro.sheet_by_index(0)
        return extrair_registros(aba.row_values(i) for i in range(aba.nrows))
    finally:
        livro.release_resources()
