"""Consolida UMA turma. Alertas nunca sao descartados automaticamente."""
from collections import defaultdict, Counter
from servicos.comparador_nomes import normalizar_nome, nome_valido, sugerir_nomes


def consolidar_frequencia(registros: list[dict], aulas: list[str]) -> list[dict]:
    if not aulas or len(set(aulas)) != len(aulas):
        raise ValueError('Informe aulas distintas.')
    if not registros:
        raise ValueError('Nenhum registro para consolidar.')
    grupos = defaultdict(list)
    for r in registros:
        if r['aula'] not in aulas or r['status'] not in ('PRESENTE', 'FALTA', 'REVISAR'):
            raise ValueError('Aula ou status invalido.')
        nome = normalizar_nome(r['nome'])
        # Identidades invalidas ficam isoladas; nao unir nomes vazios.
        chave = nome if nome_valido(nome) else f"#PENDENTE:{r['aula']}:{r['pagina']}:{r['linha']}"
        grupos[chave].append(r)
    if set(r['aula'] for r in registros) != set(aulas):
        raise ValueError('Existe aula sem registros; confira a leitura.')
    validos = [k for k in grupos if not k.startswith('#')]
    resultado = []
    for chave, linhas in sorted(grupos.items()):
        por_aula = defaultdict(list)
        for r in linhas:
            por_aula[r['aula']].append(r)
        motivos, estados = [], []
        if chave.startswith('#'):
            motivos.append('Identidade invalida')
        sugestoes = sugerir_nomes(chave, validos) if chave in validos else []
        # Similaridade em grupos incompletos pode indicar erro de OCR.
        if sugestoes and (len(por_aula) != len(aulas) or any(r['revisao_ocr'] for r in linhas)):
            motivos.append('Nomes semelhantes: ' + ', '.join(sugestoes))
        for aula in aulas:
            itens = por_aula[aula]
            if not itens:
                estado = 'NAO_LISTADO'
                motivos.append(f'{aula}: nao listado')
            elif len(itens) > 1:
                estado = 'REVISAR'
                motivos.append(f'{aula}: nome duplicado; possivel homonimo')
            else:
                r = itens[0]
                estado = r['status']
                if r['revisao_ocr']:
                    motivos.append(f'{aula}: alerta OCR')
                if estado == 'REVISAR':
                    motivos.append(f'{aula}: assinatura duvidosa')
            estados.append(estado)
        c = Counter(estados)
        # Frequencia sobre todas as aulas fornecidas; percentual final so se resolvido.
        minimo = round(100 * c['PRESENTE'] / len(aulas), 2)
        maximo = round(100 * (len(aulas) - c['FALTA']) / len(aulas), 2)
        if motivos:
            status = '100% PRELIMINAR' if c['PRESENTE'] == len(aulas) else 'REVISAR'
            frequencia = None
        else:
            status = '100% CONFIRMADO' if c['PRESENTE'] == len(aulas) else 'INFERIOR A 100%'
            frequencia = minimo
        # O nome de exibicao preserva acentos; prioriza leitura sem alerta.
        nome = max(linhas, key=lambda r: (not r['revisao_ocr'], r.get('confianca', 0)))['nome']
        resultado.append({'nome': nome, 'aulas': len(aulas), 'presentes': c['PRESENTE'],
                          'faltas': c['FALTA'], 'revisar': c['REVISAR'],
                          'nao_listado': c['NAO_LISTADO'], 'frequencia_pct': frequencia,
                          'minimo_assinaturas_pct': minimo, 'maximo_assinaturas_pct': maximo,
                          'situacao': status, 'motivos': '; '.join(motivos),
                          **{f'aula_{a}': e for a, e in zip(aulas, estados)}})
    return resultado
