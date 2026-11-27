import unittest
from servicos.automacao import consolidar_automatico
from processamento.anotacoes import palavra_trancamento

class TesteAutomacao(unittest.TestCase):
    def setUp(self):
        self.aulas=['2026-10-06','2026-10-20']
        base={'nome':'MARIA DA SILVA','numero_impresso':1,'pagina':1,'linha':1,'status':'PRESENTE','revisao_ocr':False,'motivo_ocr':'','confianca':90}
        self.r=[dict(base,aula=self.aulas[0]),dict(base,aula=self.aulas[1],revisao_ocr=True,motivo_ocr='baixa confianca')]
    def test_corroboracao(self):
        self.assertTrue(consolidar_automatico(self.r,self.aulas)[1][0]['selecionado'])
    def test_financeiro(self):
        self.assertFalse(consolidar_automatico(self.r,self.aulas,['Maria da Silva'])[1][0]['selecionado'])
    def test_trancamento(self):
        self.r[1]['trancamento_detectado']=True
        self.assertEqual(consolidar_automatico(self.r,self.aulas)[1][0]['situacao'],'MATRICULA TRANCADA')
    def test_suspeita(self):
        self.r[1]['suspeita_trancamento']=True
        self.assertFalse(consolidar_automatico(self.r,self.aulas)[1][0]['selecionado'])
    def test_termo(self):
        self.assertTrue(palavra_trancamento('trancou',90))
        self.assertFalse(palavra_trancamento('trancou',20))
        self.assertFalse(palavra_trancamento('nao trancou',90))
    def test_numero_conflitante(self):
        self.r[1]['numero_impresso']=2
        self.assertFalse(consolidar_automatico(self.r,self.aulas)[1][0]['selecionado'])
    def test_falta(self):
        self.r[1]['status']='FALTA'
        self.assertFalse(consolidar_automatico(self.r,self.aulas)[1][0]['selecionado'])
if __name__=='__main__': unittest.main(verbosity=2)
