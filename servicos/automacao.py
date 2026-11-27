from collections import defaultdict, Counter
from servicos.comparador_nomes import normalizar_nome, nome_valido
from servicos.frequencia import consolidar_frequencia
from servicos.inadimplencia import aplicar_inadimplencia


def corroborar_nomes(registros):
    registros = [dict(r) for r in registros]
    grupos, numeros = defaultdict(list), defaultdict(set)
    for r in registros:
        nome, numero = normalizar_nome(r['nome']), r.get('numero_impresso')
        grupos[nome].append(r)
        if numero is not None:
            numeros[numero].add(nome)
    for nome, grupo in grupos.items():
        nums = {r.get('numero_impresso') for r in grupo}
        datas = Counter(r['aula'] for r in grupo)
        if (not nome_valido(nome) or len(nums)!=1 or None in nums or len(datas)<2
            or max(datas.values())!=1 or len(numeros[next(iter(nums))])!=1
            or not any(not r['revisao_ocr'] for r in grupo)):
            continue
        for r in grupo:
            if r['revisao_ocr'] and r.get('motivo_ocr')=='baixa confianca':
                r.update(revisao_ocr_original=True,revisao_ocr=False,nome_corroborado=True)
    return registros


def consolidar_automatico(registros,aulas,inadimplentes=None):
    registros = corroborar_nomes(registros)
    trancados, suspeitos = set(), set()
    for r in registros:
        if r.get('trancamento_detectado') or r.get('suspeita_trancamento'):
            r['status_original'] = r['status']
            r['status'] = 'REVISAR'
        if r.get('suspeita_trancamento'):
            suspeitos.add(normalizar_nome(r['nome']))
        if r.get('trancamento_detectado') and not r['revisao_ocr'] and nome_valido(normalizar_nome(r['nome'])):
            trancados.add(normalizar_nome(r['nome']))
    resultado = aplicar_inadimplencia(consolidar_frequencia(registros,aulas),inadimplentes)
    for r in resultado:
        r['suspeita_trancamento'] = normalizar_nome(r['nome']) in suspeitos
        if r['suspeita_trancamento']:
            r['motivos'] = 'Possivel anotacao de trancamento; nao confirmado. ' + r['motivos']
        if normalizar_nome(r['nome']) in trancados and 'nome duplicado' not in r.get('motivos','') and 'Nomes semelhantes' not in r.get('motivos',''):
            r.update(situacao='MATRICULA TRANCADA',situacao_selecao='MATRICULA TRANCADA',selecionado=False,frequencia_pct=None)
            r['motivos'] = 'Anotacao de trancamento detectada automaticamente; historico preservado. ' + r['motivos']
    return registros,resultado
