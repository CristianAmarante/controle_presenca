"""Testes com dados ficticios; nenhum PDF financeiro necessario."""
import unittest
from servicos.inadimplencia import aplicar_inadimplencia


def aluno(nome, situacao='100% CONFIRMADO', pct=100):
    return {'nome': nome, 'situacao': situacao, 'frequencia_pct': pct}


class TesteInadimplencia(unittest.TestCase):
    def setUp(self):
        self.alunos = [aluno('João Ribeiro'), aluno('Maria Cardoso'),
                       aluno('Paulo Ferreira', '100% PRELIMINAR', None),
                       aluno('Lara Gomes', 'INFERIOR A 100%', 66.67)]

    def test_sem_lista(self):
        r = aplicar_inadimplencia(self.alunos)
        self.assertEqual(sum(x['selecionado'] for x in r), 2)
        self.assertTrue(all(x['situacao_financeira'] == 'NAO REALIZADA' for x in r))

    def test_nome_exato_normalizado(self):
        r = aplicar_inadimplencia(self.alunos, ['  JOAO  RIBEIRO '])
        self.assertFalse(r[0]['selecionado'])
        self.assertEqual(r[0]['situacao_selecao'], 'EXCLUIDO POR INADIMPLENCIA')
        self.assertTrue(r[1]['selecionado'])
        self.assertEqual(r[0]['frequencia_pct'], 100)
        self.assertNotIn('selecionado', self.alunos[0])

    def test_semelhanca(self):
        r = aplicar_inadimplencia(self.alunos, ['Joao Ribeira'])
        self.assertEqual(r[0]['situacao_selecao'], 'REVISAR FINANCEIRO')
        self.assertFalse(r[0]['selecionado'])

    def test_lista_vazia_validada(self):
        r = aplicar_inadimplencia(self.alunos, [])
        self.assertEqual(sum(x['selecionado'] for x in r), 2)
        self.assertEqual(r[0]['situacao_financeira'], 'NOME NAO ENCONTRADO')

    def test_lista_invalida(self):
        with self.assertRaises(ValueError):
            aplicar_inadimplencia(self.alunos, ['123'])

    def test_pendencia_academica(self):
        r = aplicar_inadimplencia(self.alunos, ['Paulo Ferreira'])
        self.assertFalse(r[2]['selecionado'])
        self.assertFalse(r[3]['selecionado'])
        self.assertEqual(r[2]['situacao_selecao'], 'PENDENCIA ACADEMICA')

    def test_nome_duplicado(self):
        r = aplicar_inadimplencia([aluno('João Ribeiro'), aluno('JOAO RIBEIRO')], ['João Ribeiro'])
        self.assertTrue(all(x['situacao_selecao'] == 'REVISAR IDENTIDADE' for x in r))
        self.assertFalse(any(x['selecionado'] for x in r))


if __name__ == '__main__':
    unittest.main(verbosity=2)
