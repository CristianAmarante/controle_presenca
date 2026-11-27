"""Filtro opcional de uma lista financeira previamente conferida.

Nao extrai PDF: a extracao depende do formato real do documento.
None significa que nao houve conferencia; [] significa lista vazia validada.
"""
from collections import Counter
from servicos.comparador_nomes import normalizar_nome, nome_valido, sugerir_nomes


def aplicar_inadimplencia(frequencia: list[dict],
                          inadimplentes: list[str] | None = None) -> list[dict]:
    """Retorna novos registros, preservando todos os campos academicos.

    Correspondencia exata de nomes nao comprova identidade; homonimos
    conhecidos e nomes semelhantes ficam pendentes de revisao.
    A lista financeira deve estar validada para a turma e periodo em questao.
    """
    lista = None
    if inadimplentes is not None:
        if not isinstance(inadimplentes, list):
            raise TypeError('Informe uma lista de nomes validada ou None.')
        lista = set()
        for nome in inadimplentes:
            if not isinstance(nome, str) or not nome_valido(normalizar_nome(nome)):
                raise ValueError('Nome financeiro invalido; confira a lista antes de aplicar.')
            lista.add(normalizar_nome(nome))

    contagem = Counter(normalizar_nome(r['nome']) for r in frequencia)
    resultado = []
    for r in frequencia:
        chave = normalizar_nome(r['nome'])
        integral = r['situacao'] == '100% CONFIRMADO'
        if integral and not nome_valido(chave):
            raise ValueError('Nome de candidato invalido; confira a frequencia.')
        status = 'NAO REALIZADA' if lista is None else 'NAO APLICAVEL'
        selecao = 'PENDENCIA ACADEMICA' if r['situacao'] in ('REVISAR', '100% PRELIMINAR') else 'FORA DA SELECAO'
        motivo = ''
        if integral:
            if contagem[chave] > 1:
                selecao = 'REVISAR IDENTIDADE'
                status = 'REVISAR IDENTIDADE' if lista is not None else status
                motivo = 'Nome duplicado na consolidacao.'
            elif lista is None:
                selecao = 'SELECIONADO POR FREQUENCIA'
            elif chave in lista:
                status = 'NOME ENCONTRADO'
                selecao = 'EXCLUIDO POR INADIMPLENCIA'
                motivo = 'Correspondencia exata na lista financeira validada.'
            elif (sugestoes := sugerir_nomes(chave, lista)):
                status = 'REVISAR CORRESPONDENCIA'
                selecao = 'REVISAR FINANCEIRO'
                motivo = 'Nomes semelhantes: ' + ', '.join(sugestoes)
            else:
                status = 'NOME NAO ENCONTRADO'
                selecao = 'SELECIONADO APOS CONFERENCIA'
        resultado.append({**r, 'situacao_financeira': status,
                          'situacao_selecao': selecao, 'motivo_financeiro': motivo,
                          'selecionado': selecao in ('SELECIONADO POR FREQUENCIA',
                                                      'SELECIONADO APOS CONFERENCIA')})
    return resultado
