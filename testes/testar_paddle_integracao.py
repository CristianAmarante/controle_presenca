import unittest
from processamento.anotacoes import classificar_anotacao, detectar_anotacoes
from servicos.automacao import consolidar_automatico
from unittest.mock import patch
import numpy as np

class TestePaddle(unittest.TestCase):
    def test_manuscrito_real(self):
        r = classificar_anotacao('taanciou', 69.16)
        self.assertTrue(r['suspeita_trancamento'])
        self.assertFalse(r['trancamento_detectado'])

    def test_duas_leituras(self):
        self.assertTrue(classificar_anotacao('TRANCOU', 95, 'TRANCOU', 92)['trancamento_detectado'])
        self.assertTrue(classificar_anotacao('TRANCOU', 95)['suspeita_trancamento'])

    def test_nao_trancou(self):
        for texto, score in [('NAO TRANCOU', 99), ('', 0), ('TAANCIOU', 20), ('MARIA SILVA', 99), ('二', 35)]:
            r = classificar_anotacao(texto, score)
            self.assertFalse(r['suspeita_trancamento'])
            self.assertFalse(r['trancamento_detectado'])

    def test_selecao(self):
        aulas = ['2026-10-06','2026-10-27']
        base = dict(nome='MARIA SILVA', numero_impresso=1, pagina=1, linha=1, status='PRESENTE', revisao_ocr=False, motivo_ocr='', confianca=99)
        registros = [dict(base,aula=a) for a in aulas]
        self.assertTrue(consolidar_automatico(registros,aulas)[1][0]['selecionado'])
        registros[1].update(classificar_anotacao('taanciou',69.16))
        r=consolidar_automatico(registros,aulas)[1][0]
        self.assertFalse(r['selecionado']); self.assertTrue(r['suspeita_trancamento'])

    def test_lote(self):
        celulas = [dict(linha=1, assinatura_tratada=np.full((30,100),255,np.uint8)),dict(linha=2)]
        with patch('processamento.anotacoes.testar_anotacoes', return_value=[dict(linha=1,texto='TRANCOU',confianca=95),dict(linha=2,texto='taanciou',confianca=69.16)]), patch('processamento.anotacoes.ler_recortes',return_value=[('TRANCOU',94)]):
            r=detectar_anotacoes(celulas)
        self.assertTrue(r[0]['trancamento_detectado']); self.assertTrue(r[1]['suspeita_trancamento'])

if __name__ == '__main__': unittest.main(verbosity=2)
