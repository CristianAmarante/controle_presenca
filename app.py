from pathlib import Path
from tempfile import TemporaryDirectory
from io import BytesIO
import hashlib
import pandas as pd
import streamlit as st
from servicos.processar_presencas import processar_presencas
from servicos.automacao import consolidar_automatico
from servicos.leitor_inadimplentes import ler_inadimplentes
from servicos.certificados import gerar_certificados, periodo_certificado

st.set_page_config(page_title='Controle de presença', page_icon='📋', layout='wide')


def motivo(r):
    if r['selecionado']: return 'Selecionado'
    if r['situacao'] == 'MATRICULA TRANCADA': return 'Anotação de trancamento identificada'
    if r.get('suspeita_trancamento'): return 'Possível matrícula trancada (não confirmada)'
    if r['situacao_selecao'] == 'EXCLUIDO POR INADIMPLENCIA': return 'Nome consta na lista financeira'
    if r['situacao_selecao'] in ('REVISAR FINANCEIRO','REVISAR IDENTIDADE'): return 'Identidade ou nome financeiro inconclusivo'
    if r['faltas']: return 'Falta detectada'
    if r.get('revisar') and r.get('nao_listado'): return 'Nome ou assinatura inconclusivo'
    if r['nao_listado']: return 'Não consta em todas as fichas'
    return 'Nome ou assinatura inconclusivo'


def tabela(rows):
    return pd.DataFrame([{'Aluno':r['nome'], 'Presenças':f"{r['presentes']} de {r['aulas']}",
        'Faltas detectadas':r['faltas'], 'Resultado':motivo(r)} for r in rows], columns=['Aluno','Presenças','Faltas detectadas','Resultado'])


def seguro(v):
    return "'"+v if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@')) else v


def excel(registros,resultado):
    buf = BytesIO()
    with pd.ExcelWriter(buf,engine='openpyxl') as w:
        for nome,df in [('Selecionados',tabela([r for r in resultado if r['selecionado']])),
                        ('Todos os alunos',tabela(resultado)),('Detalhes',pd.DataFrame(resultado)),('Registros',pd.DataFrame(registros))]:
            for c in df.columns: df[c]=df[c].map(seguro)
            df.to_excel(w,sheet_name=nome,index=False)
            ws=w.sheets[nome]; ws.freeze_panes='A2'; ws.auto_filter.ref=ws.dimensions
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width=min(70,max(15,max(len(str(c.value or '')) for c in col)+2))
    return buf.getvalue()


st.title('Controle de presença')
st.caption('Envie os documentos e obtenha a lista de alunos com presença em todas as aulas. OCR: PP-OCRv6 Medium.')
with st.sidebar:
    st.header('1. Documentos')
    turma=st.text_input('Código da turma',placeholder='FS40').strip().upper()
    pdfs=st.file_uploader('Fichas de presença (.pdf)',type=['pdf'],accept_multiple_files=True)
    st.caption('Exemplo: FS40 06.10.2026 (1).pdf. Envie todas as fichas do período.')
    fin=st.file_uploader('Lista de inadimplentes (.xls) — opcional',type=['xls'])
    st.caption('Sem o Excel, a seleção considera apenas a presença. Use o relatório financeiro do período correto.')
    iniciar=st.button('Processar documentos',type='primary')
    if st.button('Limpar resultados'):
        st.session_state.pop('auto_resultado',None)
        st.session_state.pop('auto_academico',None)
        st.session_state.pop('auto_certificados',None)
    st.caption('Uso institucional autorizado. Processamento local; resultados ficam na sessão.')

# Vincula o resultado aos documentos atuais, evitando exportacao desatualizada.
chave=(turma,tuple(sorted((a.name,hashlib.sha256(a.getvalue()).hexdigest()) for a in pdfs)),
       (fin.name,hashlib.sha256(fin.getvalue()).hexdigest()) if fin else None)
if iniciar:
    st.session_state.pop('auto_resultado',None)
    st.session_state.pop('auto_certificados',None)
    if not turma or not pdfs:
        st.warning('Informe a turma e envie pelo menos uma ficha de presença.')
    else:
        barra=st.progress(0,text='Analisando documentos…')
        try:
            nomes_fin=None
            if fin is not None:
                with TemporaryDirectory(prefix='financeiro_') as pasta:
                    p=Path(pasta)/'relatorio.xls'; p.write_bytes(fin.getvalue())
                    nomes_fin=[r['nome'] for r in ler_inadimplentes(p)]
            # Reusa o processamento academico quando apenas o financeiro muda.
            cache=st.session_state.get('auto_academico')
            if cache and cache[0]==chave[:2]:
                registros,aulas=cache[1:]
            else:
                registros,aulas,_=processar_presencas([(a.name,a.getvalue()) for a in pdfs],turma,lambda i,n:barra.progress(i/n,text=f'Fichas analisadas: {i} de {n}'))
                st.session_state['auto_academico']=(chave[:2],registros,aulas)
            registros,resultado=consolidar_automatico(registros,aulas,nomes_fin)
            st.session_state['auto_resultado']=(chave,registros,aulas,resultado,None if nomes_fin is None else len(nomes_fin))
        except Exception as e:
            st.error(f'Não foi possível concluir o processamento: {e}')
        finally:
            barra.empty()

lote=st.session_state.get('auto_resultado')
if not lote or lote[0]!=chave:
    st.subheader('Como começar')
    st.info('Informe a turma, envie as fichas e clique em Processar documentos. Se quiser, envie também a lista financeira.')
    st.stop()
_,registros,aulas,resultado,nfin=lote
selecionados=[r for r in resultado if r['selecionado']]
trancados=[r for r in resultado if r['situacao']=='MATRICULA TRANCADA']
inconclusivos=[r for r in resultado if not r['selecionado'] and motivo(r) in ('Nome ou assinatura inconclusivo','Não consta em todas as fichas','Identidade ou nome financeiro inconclusivo','Possível matrícula trancada (não confirmada)')]
excluidos=[r for r in resultado if r['situacao_selecao']=='EXCLUIDO POR INADIMPLENCIA']
st.subheader('2. Resultado da análise automática')
st.caption(f'Turma {turma} · {len(aulas)} aula(s) · {aulas[0]} a {aulas[-1]}')
a,b,c,d=st.columns(4)
a.metric('Alunos identificados',len(resultado)); b.metric('Selecionados',len(selecionados)); c.metric('Trancamentos identificados',len(trancados)); d.metric('Não conclusivos',len(inconclusivos))
if nfin is None: st.info('Filtro financeiro não aplicado. Resultado baseado somente nas fichas.')
else: st.info(f'Filtro financeiro aplicado: {nfin} registros; {len(excluidos)} candidatos encontrados na lista. Ausência do nome não comprova quitação.')
if inconclusivos: st.warning('Registros que o sistema não conseguiu interpretar ficaram fora da seleção. Não é necessário corrigir para baixar o relatório.')
st.markdown('### Alunos selecionados')
st.write('Presença detectada em todas as fichas enviadas, sem pendências de identificação e conforme o filtro escolhido.')
if selecionados: st.dataframe(tabela(selecionados),hide_index=True,use_container_width=True)
else: st.info('Nenhum aluno atendeu aos critérios automáticos.')
st.download_button('Baixar relatório Excel',excel(registros,resultado),file_name=f'frequencia_{turma}.xlsx',mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',type='primary')
st.markdown('### Certificados Aluno Nota 10')
mes_cert, ano_cert = periodo_certificado(aulas)
st.caption(f'Mês de referência: {mes_cert.capitalize()} de {ano_cert} · Sede Sul')
if len({a[:7] for a in aulas}) > 1:
    st.warning('As fichas abrangem mais de um mês. O certificado usa o mês da ficha mais recente. Para premiar um único mês, envie apenas as fichas daquele período.')
if not selecionados:
    st.session_state.pop('auto_certificados',None)
    st.info('Nenhum certificado gerado, pois não há alunos selecionados.')
else:
    try:
        cache_cert = st.session_state.get('auto_certificados')
        if not cache_cert or cache_cert[0] != chave:
            with st.spinner('Preparando certificados...'):
                pacote = gerar_certificados(resultado,aulas)
            st.session_state['auto_certificados'] = (chave,pacote)
        else:
            pacote = cache_cert[1]
        st.success(f"{len(pacote['arquivos'])} certificado(s) pronto(s).")
        st.download_button('Baixar todos os certificados (ZIP)',pacote['zip'],
                           file_name=f'certificados_{turma}_{mes_cert}_{ano_cert}.zip',
                           mime='application/zip',type='primary',key='baixar_certificados_zip')
        with st.expander('Baixar certificados individualmente'):
            for i,item in enumerate(pacote['arquivos']):
                st.download_button(item['nome'],item['pdf'],file_name=item['arquivo'],
                                   mime='application/pdf',key=f'certificado_{i}')
    except Exception as e:
        st.session_state.pop('auto_certificados',None)
        st.error(f'Não foi possível gerar os certificados: {e}. O relatório de frequência continua disponível.')
st.caption('Modelo institucional fornecido, com Sede Sul e assinatura impressa. Emissão restrita a uso autorizado; a análise automática verifica presença e o filtro escolhido, não participação ou desempenho.')
with st.expander(f'Por que os outros alunos ficaram de fora? ({len(resultado)-len(selecionados)})'):
    st.dataframe(tabela([r for r in resultado if not r['selecionado']]),hide_index=True,use_container_width=True)
with st.expander('Ver presença de todos por data'):
    rotulos={'PRESENTE':'Presente','FALTA':'Falta','REVISAR':'Não conclusivo','NAO_LISTADO':'Não consta'}
    st.dataframe(pd.DataFrame([{'Aluno':r['nome'],**{a:rotulos[r['aula_'+a]] for a in aulas},'Resultado':motivo(r)} for r in resultado]),hide_index=True,use_container_width=True)
st.caption('A leitura de anotações manuscritas pelo PaddleOCR é experimental. O relatório é uma análise automatizada das fichas, não uma confirmação oficial de matrícula ou presença.')
