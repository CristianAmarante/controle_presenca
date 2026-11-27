import unittest
from io import BytesIO
from zipfile import ZipFile
import pymupdf
from servicos.certificados import gerar_certificados, periodo_certificado

AULAS=['2026-10-06','2026-10-27','2026-10-20']

class TesteCertificados(unittest.TestCase):
    def test_periodo(self):
        self.assertEqual(periodo_certificado(AULAS),('outubro',2026))
        self.assertEqual(periodo_certificado(['2026-12-30','2027-01-02']),('janeiro',2027))
    def test_selecao_e_zip(self):
        r=[{'nome':'João da Silva','selecionado':True},
           {'nome':'Pessoa Excluída','selecionado':False},
           {'nome':'Ana Souza','selecionado':True}]
        p=gerar_certificados(r,AULAS)
        self.assertEqual(len(p['arquivos']),2)
        with ZipFile(BytesIO(p['zip'])) as z:
            self.assertEqual(len(z.namelist()),2)
            self.assertIsNone(z.testzip())
            for a in p['arquivos']:
                self.assertEqual(z.read(a['arquivo']),a['pdf'])
                with pymupdf.open(stream=a['pdf'],filetype='pdf') as doc:
                    self.assertEqual(len(doc),1)
                    self.assertGreater(doc[0].rect.width,doc[0].rect.height)
                    self.assertIn(a['nome'],doc[0].get_text())
                    self.assertIn('outubro',doc[0].get_text())
                    self.assertNotIn('EXCLUÍDA',doc[0].get_text())
    def test_sem_selecionados(self):
        p=gerar_certificados([{'nome':'Ana Souza','selecionado':False}],AULAS)
        self.assertIsNone(p['zip']); self.assertEqual(p['arquivos'],[])
    def test_colisao_nomes(self):
        p=gerar_certificados([{'nome':'João Silva','selecionado':True},{'nome':'Joao Silva','selecionado':True}],AULAS)
        self.assertEqual(len({a['arquivo'] for a in p['arquivos']}),2)
    def test_nome_longo(self):
        nome='MARIA CLARA DE ALMEIDA RODRIGUES DOS SANTOS FERREIRA E SOUZA'
        p=gerar_certificados([{'nome':nome,'selecionado':True}],AULAS)
        with pymupdf.open(stream=p['arquivos'][0]['pdf'],filetype='pdf') as doc:
            self.assertIn(nome,doc[0].get_text())
    def test_status_ausente(self):
        self.assertEqual(gerar_certificados([{'nome':'Ana Souza'}],AULAS)['arquivos'],[])

if __name__=='__main__':
    unittest.main(verbosity=2)
