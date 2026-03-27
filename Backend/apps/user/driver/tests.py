"""
Tests for Auth03 — POST /auth/registo-motorista

Acceptance Criteria:
  AC1 — CP 1000-001 preenche localidade automaticamente
  AC2 — CP inválido retorna 400 com mensagem específica
  AC3 — ano_nascimento < 18 anos retorna 400
  AC4 — Falha em motoristas reverte inserção em utilizadores
  AC5 — Registo bem-sucedido retorna 201 sem senha_hash
"""

import json
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.urls import reverse

from apps.user.models import User
from .models import Driver


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

URL = '/auth/registo-motorista'

VALID_PAYLOAD = {
    'username':           'joao_motorista',
    'email':              'joao@example.com',
    'password':           'Seguro123',
    'name':               'João Silva',
    'nif':                '123456789',   # mod-11 valid: check = 9
    'ano_nascimento':     1990,
    'genero':             'M',
    'num_carta_conducao': 'ABC12',
    'codigo_postal':      '1000-001',
}


def _mock_cp_response(localidade='LISBOA'):
    """Cria um mock de requests.get que retorna um CP válido."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [{'Localidade': localidade}]
    return mock_resp


def _mock_cp_not_found():
    """Cria um mock de requests.get que simula CP não encontrado."""
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.json.return_value = []
    return mock_resp


# ---------------------------------------------------------------------------
# AC1 — CP 1000-001 preenche localidade automaticamente
# ---------------------------------------------------------------------------

class AC1_CodigoPostalPreencheLocalidade(TestCase):
    """CP válido deve preencher a localidade automaticamente a partir da API."""

    @patch('apps.user.driver.views.requests.get', return_value=_mock_cp_response('LISBOA'))
    def test_localidade_preenchida_automaticamente(self, mock_get):
        resp = self.client.post(
            URL,
            data=json.dumps(VALID_PAYLOAD),
            content_type='application/json',
        )

        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertEqual(body['user']['localidade'], 'LISBOA')
        self.assertEqual(body['user']['codigo_postal'], '1000-001')

        # Confirm the API was called with the correct URL segment
        call_url = mock_get.call_args[0][0]
        self.assertIn('1000', call_url)
        self.assertIn('001', call_url)

    @patch('apps.user.driver.views.requests.get', return_value=_mock_cp_response('PORTO'))
    def test_localidade_diferente_preenchida(self, _mock):
        payload = {**VALID_PAYLOAD, 'codigo_postal': '4000-007', 'email': 'porto@example.com', 'username': 'porto_user'}
        resp = self.client.post(URL, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()['user']['localidade'], 'PORTO')


# ---------------------------------------------------------------------------
# AC2 — CP inválido retorna 400 com mensagem específica
# ---------------------------------------------------------------------------

class AC2_CodigoPostalInvalido(TestCase):
    """Pedidos com CP inexistente ou em formato errado devem retornar 400."""

    def test_formato_errado_sem_hifen(self):
        payload = {**VALID_PAYLOAD, 'codigo_postal': '1000001'}
        resp = self.client.post(URL, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('inválido', resp.json()['message'].lower())

    def test_formato_errado_letras(self):
        payload = {**VALID_PAYLOAD, 'codigo_postal': 'ABCD-EFG'}
        resp = self.client.post(URL, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 400)

    @patch('apps.user.driver.views.requests.get', return_value=_mock_cp_not_found())
    def test_cp_nao_encontrado_retorna_400(self, _mock):
        payload = {**VALID_PAYLOAD, 'codigo_postal': '9999-999'}
        resp = self.client.post(URL, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('não encontrado', resp.json()['message'].lower())

    @patch('apps.user.driver.views.requests.get', return_value=_mock_cp_not_found())
    def test_mensagem_especifica_retornada(self, _mock):
        payload = {**VALID_PAYLOAD, 'codigo_postal': '0000-000'}
        resp = self.client.post(URL, data=json.dumps(payload), content_type='application/json')
        self.assertIn('message', resp.json())
        self.assertIsInstance(resp.json()['message'], str)
        self.assertGreater(len(resp.json()['message']), 0)


# ---------------------------------------------------------------------------
# AC3 — ano_nascimento < 18 anos retorna 400
# ---------------------------------------------------------------------------

class AC3_AnoNascimentoMenoridade(TestCase):
    """Condutor com menos de 18 anos deve ser rejeitado."""

    from datetime import date
    _ano_atual = date.today().year

    @patch('apps.user.driver.views.requests.get', return_value=_mock_cp_response())
    def test_menor_18_rejeitado(self, _mock):
        from datetime import date
        payload = {**VALID_PAYLOAD, 'ano_nascimento': date.today().year - 17}
        resp = self.client.post(URL, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('18', resp.json()['message'])

    @patch('apps.user.driver.views.requests.get', return_value=_mock_cp_response())
    def test_exatamente_18_aceite(self, _mock):
        from datetime import date
        payload = {**VALID_PAYLOAD, 'ano_nascimento': date.today().year - 18}
        resp = self.client.post(URL, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 201)

    @patch('apps.user.driver.views.requests.get', return_value=_mock_cp_response())
    def test_nascimento_antes_1900_rejeitado(self, _mock):
        payload = {**VALID_PAYLOAD, 'ano_nascimento': 1899}
        resp = self.client.post(URL, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('1900', resp.json()['message'])

    @patch('apps.user.driver.views.requests.get', return_value=_mock_cp_response())
    def test_campo_nao_numerico_rejeitado(self, _mock):
        payload = {**VALID_PAYLOAD, 'ano_nascimento': 'mil novecentos'}
        resp = self.client.post(URL, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 400)


# ---------------------------------------------------------------------------
# AC4 — Falha em Motorista reverte inserção em User (transação atómica)
# ---------------------------------------------------------------------------

class AC4_TransacaoAtomica(TestCase):
    """Se a criação do Motorista falhar, o User não deve ficar na base de dados."""

    @patch('apps.user.driver.views.requests.get', return_value=_mock_cp_response())
    def test_falha_motorista_reverte_user(self, _mock):
        original_user_count = User.objects.count()

        with patch('apps.user.driver.models.Driver.objects.create') as mock_create:
            mock_create.side_effect = Exception('DB failure simulada')
            resp = self.client.post(
                URL,
                data=json.dumps(VALID_PAYLOAD),
                content_type='application/json',
            )

        self.assertEqual(resp.status_code, 500)
        # O User NÃO deve ter sido persistido
        self.assertEqual(User.objects.count(), original_user_count)
        self.assertFalse(User.objects.filter(username='joao_motorista').exists())

    @patch('apps.user.driver.views.requests.get', return_value=_mock_cp_response())
    def test_sucesso_persiste_ambos(self, _mock):
        resp = self.client.post(
            URL,
            data=json.dumps(VALID_PAYLOAD),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(User.objects.filter(username='joao_motorista').exists())
        user = User.objects.get(username='joao_motorista')
        self.assertTrue(Driver.objects.filter(user_ptr=user).exists())


# ---------------------------------------------------------------------------
# AC5 — Registo bem-sucedido retorna 201 sem senha_hash
# ---------------------------------------------------------------------------

class AC5_RegistoBemSucedido(TestCase):
    """Registo válido retorna 201; a resposta não deve conter password nem password_hash."""

    @patch('apps.user.driver.views.requests.get', return_value=_mock_cp_response('LISBOA'))
    def test_retorna_201(self, _mock):
        resp = self.client.post(
            URL,
            data=json.dumps(VALID_PAYLOAD),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 201)

    @patch('apps.user.driver.views.requests.get', return_value=_mock_cp_response('LISBOA'))
    def test_nao_expoe_password(self, _mock):
        resp = self.client.post(
            URL,
            data=json.dumps(VALID_PAYLOAD),
            content_type='application/json',
        )
        body = resp.json()
        user_data = body.get('user', {})
        self.assertNotIn('password', user_data)
        self.assertNotIn('password_hash', user_data)
        self.assertNotIn('senha_hash', user_data)

    @patch('apps.user.driver.views.requests.get', return_value=_mock_cp_response('LISBOA'))
    def test_campos_esperados_presentes(self, _mock):
        resp = self.client.post(
            URL,
            data=json.dumps(VALID_PAYLOAD),
            content_type='application/json',
        )
        body = resp.json()
        self.assertTrue(body.get('success'))
        user_data = body['user']
        for campo in ('id', 'username', 'email', 'name', 'role',
                      'ano_nascimento', 'genero', 'num_carta_conducao',
                      'localidade', 'codigo_postal'):
            self.assertIn(campo, user_data, msg=f"Campo '{campo}' em falta na resposta")
        self.assertEqual(user_data['role'], 'motorista')

    @patch('apps.user.driver.views.requests.get', return_value=_mock_cp_response())
    def test_password_armazenada_com_hash(self, _mock):
        """A password guardada na BD não deve ser o texto original."""
        self.client.post(
            URL,
            data=json.dumps(VALID_PAYLOAD),
            content_type='application/json',
        )
        user = User.objects.get(username='joao_motorista')
        self.assertNotEqual(user.password, VALID_PAYLOAD['password'])
        self.assertTrue(user.password.startswith('$2b$') or user.password.startswith('$2a$'))

    @patch('apps.user.driver.views.requests.get', return_value=_mock_cp_response())
    def test_username_duplicado_retorna_409(self, _mock):
        self.client.post(URL, data=json.dumps(VALID_PAYLOAD), content_type='application/json')
        payload2 = {**VALID_PAYLOAD, 'email': 'outro@example.com'}
        resp = self.client.post(URL, data=json.dumps(payload2), content_type='application/json')
        self.assertEqual(resp.status_code, 409)

    @patch('apps.user.driver.views.requests.get', return_value=_mock_cp_response())
    def test_email_duplicado_retorna_409(self, _mock):
        self.client.post(URL, data=json.dumps(VALID_PAYLOAD), content_type='application/json')
        payload2 = {**VALID_PAYLOAD, 'username': 'outro_user'}
        resp = self.client.post(URL, data=json.dumps(payload2), content_type='application/json')
        self.assertEqual(resp.status_code, 409)


# ---------------------------------------------------------------------------
# Extra — validações de campos individuais
# ---------------------------------------------------------------------------

class ValidacaoCampos(TestCase):
    """Testes de validação de genero e num_carta_conducao."""

    @patch('apps.user.driver.views.requests.get', return_value=_mock_cp_response())
    def test_genero_invalido_retorna_400(self, _mock):
        payload = {**VALID_PAYLOAD, 'genero': 'X'}
        resp = self.client.post(URL, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 400)

    @patch('apps.user.driver.views.requests.get', return_value=_mock_cp_response())
    def test_genero_outro_aceite(self, _mock):
        payload = {**VALID_PAYLOAD, 'genero': 'Outro'}
        resp = self.client.post(URL, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 201)

    @patch('apps.user.driver.views.requests.get', return_value=_mock_cp_response())
    def test_carta_muito_curta_rejeitada(self, _mock):
        payload = {**VALID_PAYLOAD, 'num_carta_conducao': 'AB1'}
        resp = self.client.post(URL, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 400)

    @patch('apps.user.driver.views.requests.get', return_value=_mock_cp_response())
    def test_carta_com_caracteres_especiais_rejeitada(self, _mock):
        payload = {**VALID_PAYLOAD, 'num_carta_conducao': 'AB-123'}
        resp = self.client.post(URL, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 400)

    def test_campos_obrigatorios_em_falta(self):
        resp = self.client.post(URL, data=json.dumps({}), content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('message', resp.json())
