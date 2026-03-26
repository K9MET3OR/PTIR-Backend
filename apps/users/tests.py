"""
Tests for Auth04 — POST /auth/login (NIF + password → JWT)

Acceptance Criteria:
  AC1 — NIF inválido retorna 400 sem consultar BD
  AC2 — NIF correto + senha errada retorna 401 com 'Credenciais inválidas'
  AC3 — NIF inexistente retorna 401 com 'Credenciais inválidas' (mesma mensagem)
  AC4 — Credenciais válidas retorna 200 com { token, role, nome }
  AC5 — JWT decodificado contém { id, nif, role, iat, exp }

Also covers the NIF mod-11 validator utility.
"""

import json
from unittest.mock import patch

import bcrypt
import jwt
from django.conf import settings
from django.test import TestCase

from apps.users.models import User
from apps.users.utils import validar_nif

URL = '/auth/login'

# ---------------------------------------------------------------------------
# Known valid Portuguese NIFs (mod-11 compliant) for fixture use
# ---------------------------------------------------------------------------
_VALID_NIF   = '123456789'   # fictitious but mod-11 valid
_INVALID_NIF = '123456788'   # fails mod-11 check


def _make_valid_nif():
    """Return a NIF that passes the mod-11 algorithm."""
    # 12345678? → sum = 1*9+2*8+3*7+4*6+5*5+6*4+7*3+8*2 = 9+16+21+24+25+24+21+16 = 156
    # 156 % 11 = 2 → check = 11-2 = 9 → NIF = 123456789
    return '123456789'


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def _create_user(nif=_VALID_NIF, password='Seguro123', role='motorista'):
    hashed = _hash(password)
    return User.objects.create(
        username=f'user_{nif}',
        email=f'{nif}@example.com',
        password=hashed,
        name='Test User',
        role=role,
        nif=nif,
    )


# ---------------------------------------------------------------------------
# Unit tests — NIF mod-11 validator
# ---------------------------------------------------------------------------

class ValidadorNIFTests(TestCase):
    """Tests for apps.users.utils.validar_nif"""

    def test_nif_valido_aceite(self):
        self.assertTrue(validar_nif('123456789'))

    def test_nif_menos_9_digitos_rejeitado(self):
        self.assertFalse(validar_nif('12345678'))

    def test_nif_mais_9_digitos_rejeitado(self):
        self.assertFalse(validar_nif('1234567890'))

    def test_nif_com_letras_rejeitado(self):
        self.assertFalse(validar_nif('12345678A'))

    def test_nif_vazio_rejeitado(self):
        self.assertFalse(validar_nif(''))

    def test_nif_none_rejeitado(self):
        self.assertFalse(validar_nif(None))

    def test_nif_digito_check_errado_rejeitado(self):
        self.assertFalse(validar_nif(_INVALID_NIF))

    def test_nif_primeiro_digito_zero_rejeitado(self):
        # Starts with 0 → invalid Portuguese NIF
        self.assertFalse(validar_nif('012345678'))


# ---------------------------------------------------------------------------
# AC1 — NIF inválido retorna 400 sem consultar BD
# ---------------------------------------------------------------------------

class AC1_NIFInvalido(TestCase):
    """Invalid NIF format/checksum must return 400 before any DB query."""

    @patch('apps.users.models.User.objects')
    def test_nif_invalido_nao_consulta_bd(self, mock_objects):
        resp = self.client.post(
            URL,
            data=json.dumps({'nif': _INVALID_NIF, 'password': 'qualquer'}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)
        mock_objects.get.assert_not_called()

    def test_nif_invalido_retorna_400(self):
        resp = self.client.post(
            URL,
            data=json.dumps({'nif': _INVALID_NIF, 'password': 'qualquer'}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn('message', resp.json())

    def test_nif_letras_retorna_400(self):
        resp = self.client.post(
            URL,
            data=json.dumps({'nif': 'ABCDEFGHI', 'password': 'qualquer'}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_nif_curto_retorna_400(self):
        resp = self.client.post(
            URL,
            data=json.dumps({'nif': '12345', 'password': 'qualquer'}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_nif_ausente_retorna_400(self):
        resp = self.client.post(
            URL,
            data=json.dumps({'password': 'qualquer'}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)


# ---------------------------------------------------------------------------
# AC2 — NIF correto + senha errada retorna 401 com 'Credenciais inválidas'
# ---------------------------------------------------------------------------

class AC2_SenhaErrada(TestCase):
    """Right NIF, wrong password → 401 with generic message."""

    def setUp(self):
        self.user = _create_user(password='SenhaCorreta1')

    def test_senha_errada_retorna_401(self):
        resp = self.client.post(
            URL,
            data=json.dumps({'nif': _VALID_NIF, 'password': 'SenhaErrada1'}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 401)

    def test_senha_errada_mensagem_generica(self):
        resp = self.client.post(
            URL,
            data=json.dumps({'nif': _VALID_NIF, 'password': 'SenhaErrada1'}),
            content_type='application/json',
        )
        self.assertEqual(resp.json()['message'], 'Credenciais inválidas')

    def test_senha_vazia_retorna_400(self):
        resp = self.client.post(
            URL,
            data=json.dumps({'nif': _VALID_NIF, 'password': ''}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)


# ---------------------------------------------------------------------------
# AC3 — NIF inexistente retorna 401 com 'Credenciais inválidas' (mesma msg)
# ---------------------------------------------------------------------------

class AC3_NIFInexistente(TestCase):
    """NIF that passes mod-11 but does not exist → 401, same generic message."""

    # A second mod-11-valid NIF not present in any test fixture:
    # sum = 2*9+4*8+3*7+5*6+9*5+8*4+9*3+8*2 = 221 → 221%11=1 < 2 → check=0
    _UNKNOWN_NIF = '243598980'

    def test_nif_inexistente_retorna_401(self):
        resp = self.client.post(
            URL,
            data=json.dumps({'nif': self._UNKNOWN_NIF, 'password': 'qualquer'}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 401)

    def test_nif_inexistente_mensagem_igual_senha_errada(self):
        """The error message must be identical to AC2 to prevent user enumeration."""
        resp = self.client.post(
            URL,
            data=json.dumps({'nif': self._UNKNOWN_NIF, 'password': 'qualquer'}),
            content_type='application/json',
        )
        self.assertEqual(resp.json()['message'], 'Credenciais inválidas')


# ---------------------------------------------------------------------------
# AC4 — Credenciais válidas retorna 200 com { token, role, nome }
# ---------------------------------------------------------------------------

class AC4_CredenciaisValidas(TestCase):
    """Valid NIF + correct password → 200 with token, role, nome."""

    def setUp(self):
        self.password = 'SenhaCorreta1'
        self.user = _create_user(password=self.password, role='motorista')

    def test_retorna_200(self):
        resp = self.client.post(
            URL,
            data=json.dumps({'nif': _VALID_NIF, 'password': self.password}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)

    def test_resposta_contem_token(self):
        resp = self.client.post(
            URL,
            data=json.dumps({'nif': _VALID_NIF, 'password': self.password}),
            content_type='application/json',
        )
        body = resp.json()
        self.assertIn('token', body)
        self.assertIsInstance(body['token'], str)
        self.assertGreater(len(body['token']), 10)

    def test_resposta_contem_role(self):
        resp = self.client.post(
            URL,
            data=json.dumps({'nif': _VALID_NIF, 'password': self.password}),
            content_type='application/json',
        )
        self.assertIn('role', resp.json())
        self.assertEqual(resp.json()['role'], 'motorista')

    def test_resposta_contem_nome(self):
        resp = self.client.post(
            URL,
            data=json.dumps({'nif': _VALID_NIF, 'password': self.password}),
            content_type='application/json',
        )
        self.assertIn('nome', resp.json())
        self.assertEqual(resp.json()['nome'], self.user.name)

    def test_resposta_nao_contem_password(self):
        resp = self.client.post(
            URL,
            data=json.dumps({'nif': _VALID_NIF, 'password': self.password}),
            content_type='application/json',
        )
        body = resp.json()
        self.assertNotIn('password', body)
        self.assertNotIn('password_hash', body)


# ---------------------------------------------------------------------------
# AC5 — JWT decodificado contém { id, nif, role, iat, exp }
# ---------------------------------------------------------------------------

class AC5_JWTPayload(TestCase):
    """Decode the returned JWT and verify its payload fields."""

    def setUp(self):
        self.password = 'SenhaCorreta1'
        self.user = _create_user(password=self.password)

    def _get_token(self):
        resp = self.client.post(
            URL,
            data=json.dumps({'nif': _VALID_NIF, 'password': self.password}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        return resp.json()['token']

    def test_jwt_contem_id(self):
        token = self._get_token()
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=['HS256'])
        self.assertIn('id', payload)
        self.assertEqual(payload['id'], str(self.user.id))

    def test_jwt_contem_nif(self):
        token = self._get_token()
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=['HS256'])
        self.assertIn('nif', payload)
        self.assertEqual(payload['nif'], _VALID_NIF)

    def test_jwt_contem_role(self):
        token = self._get_token()
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=['HS256'])
        self.assertIn('role', payload)
        self.assertEqual(payload['role'], self.user.role)

    def test_jwt_contem_iat(self):
        token = self._get_token()
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=['HS256'])
        self.assertIn('iat', payload)
        self.assertIsInstance(payload['iat'], int)

    def test_jwt_contem_exp(self):
        token = self._get_token()
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=['HS256'])
        self.assertIn('exp', payload)
        self.assertIsInstance(payload['exp'], int)

    def test_jwt_exp_maior_que_iat(self):
        token = self._get_token()
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=['HS256'])
        self.assertGreater(payload['exp'], payload['iat'])

    def test_jwt_expira_em_24h(self):
        token = self._get_token()
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=['HS256'])
        delta_seconds = payload['exp'] - payload['iat']
        expected = settings.JWT_EXPIRY_HOURS * 3600
        self.assertAlmostEqual(delta_seconds, expected, delta=5)
