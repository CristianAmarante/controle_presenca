from pathlib import Path
from collections import Counter
import argparse
import csv
import unittest
from servicos.leitor_inadimplentes import extrair_registros, ler_inadimplentes
from servicos.inadimplencia import aplicar_inadimplencia

CAB = ['Aluno', 'Nº Matrícula', 'Nº Parcelas']

class TesteLeitor(unittest.TestCase):
    def test_valido(self):
        r = extrair_registros([['Titulo'], CAB, ['Maria Silva', '001', 1], ['Total de Registros: 1']])
        self.assertEqual(r, [{'nome':'Maria Silva','matricula':'001','parcelas':1}])
    def test_vazio_validado(self):
        self.assertEqual(extrair_registros([CAB, ['Total de Registros: 0']]), [])
    def test_total_divergente(self):
        with self.assertRaises(ValueError):
            extrair_registros([CAB, ['Total de Registros: 2']])
    def test_nome_invalido(self):
        with self.assertRaises(ValueError):
            extrair_registros([CAB, ['?', '001', 1], ['Total de Registros: 1']])
    def test_homonimo(self):
        with self.assertRaises(ValueError):
            extrair_registros([CAB, ['Maria Silva','001',1], ['Maria Silva','002',1], ['Total de Registros: 2']])
    def test_filtro_integrado(self):
        r = aplicar_inadimplencia([{'nome':'Maria Silva','situacao':'100% CONFIRMADO'}], ['Maria Silva'])
        self.assertFalse(r[0]['selecionado'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--arquivo', type=Path)
    parser.add_argument('--aplicar', action='store_true', help='Confirma escopo da lista financeira e executa cruzamento de teste.')
    args = parser.parse_args()
    if args.aplicar and not args.arquivo:
        parser.error('--aplicar exige --arquivo')
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TesteLeitor)
    if not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful():
        raise SystemExit(1)
    if args.arquivo is None:
        return
    registros = ler_inadimplentes(args.arquivo)
    print(f'\nRegistros financeiros validados estruturalmente: {len(registros)}')
    for parcelas, quantidade in sorted(Counter(r['parcelas'] for r in registros).items()):
        print(f'{parcelas} parcela(s): {quantidade} aluno(s)')
    if not args.aplicar:
        print('Somente importacao. Confira os filtros e o periodo do relatorio antes de aplicar.')
        return
    raiz = Path(__file__).resolve().parents[1]
    caminho = raiz / 'dados' / 'saida' / 'frequencia' / 'frequencia_consolidada.csv'
    with caminho.open(encoding='utf-8-sig', newline='') as f:
        frequencia = list(csv.DictReader(f, delimiter=';'))
    if not frequencia:
        raise ValueError('Relatorio de frequencia vazio.')
    resultado = aplicar_inadimplencia(frequencia, [r['nome'] for r in registros])
    print('\nSimulacao de cruzamento (nao altera o relatorio academico):')
    for status, n in sorted(Counter(r['situacao_selecao'] for r in resultado).items()):
        print(f'{status}: {n}')
    print(f"Selecionados pelo algoritmo: {sum(r['selecionado'] for r in resultado)}")

if __name__ == '__main__':
    main()
