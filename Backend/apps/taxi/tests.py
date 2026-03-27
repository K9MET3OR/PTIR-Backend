"""
Tests for POST /auth/taxi/registo-taxi (registo de veiculo taxi)

Acceptance Criteria:
  AC1 — Pedido sem campos obrigatorios retorna 400 com mensagem que lista os em falta
  AC2 — modelo com menos de 2 caracteres retorna 400
  AC3 — matricula demasiado curta retorna 400
  AC4 — ano_compra invalido (nao numerico / fora do intervalo) retorna 400
  AC5 — Registo valido retorna 201 com success e objeto taxi (sem campos internos extra)
  AC6 — Matricula duplicada retorna 409

Also covers apps.taxi.views.validate_taxi_payload directly (unit tests).
"""

import json
from datetime import date

from django.test import TestCase

from apps.taxi.models import Taxi
from apps.taxi.views import validate_taxi_payload

URL = '/auth/taxi/registo-taxi'

# ---------------------------------------------------------------------------
# Payload base valido (matricula unica por teste quando necessario)
# ---------------------------------------------------------------------------

_VALID_PAYLOAD = {
    'modelo': 'Toyota Corolla',
    'matricula': 'ZZ-99-XX',
    'ano_compra': 2020,
}


def _payload(**overrides):
    return {**_VALID_PAYLOAD, **overrides}


# ---------------------------------------------------------------------------
# Unit tests — validate_taxi_payload (sem HTTP)
# ---------------------------------------------------------------------------

class ValidadorTaxiPayloadTests(TestCase):
    """Tests for apps.taxi.views.validate_taxi_payload"""

    def test_payload_valido_retorna_none(self):
        self.assertIsNone(validate_taxi_payload(_VALID_PAYLOAD))

    def test_modelo_ausente_retorna_erro(self):
        data = {k: v for k, v in _VALID_PAYLOAD.items() if k != 'modelo'}
        err = validate_taxi_payload(data)
        self.assertIsNotNone(err)
        self.assertIn('modelo', err)

    def test_matricula_vazia_retorna_erro(self):
        err = validate_taxi_payload(_payload(matricula=''))
        self.assertIsNotNone(err)

    def test_ano_compra_ausente_retorna_erro(self):
        data = {k: v for k, v in _VALID_PAYLOAD.items() if k != 'ano_compra'}
        err = validate_taxi_payload(data)
        self.assertIsNotNone(err)
        self.assertIn('ano_compra', err)


# ---------------------------------------------------------------------------
# AC1 — Campos obrigatorios em falta → 400
# ---------------------------------------------------------------------------

class AC1_CamposObrigatorios(TestCase):
    """Missing required fields must return 400 with a clear message."""

    def test_corpo_vazio_retorna_400(self):
        resp = self.client.post(URL, data=json.dumps({}), content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('message', resp.json())

    def test_lista_campos_em_falta_na_mensagem(self):
        resp = self.client.post(URL, data=json.dumps({}), content_type='application/json')
        msg = resp.json().get('message', '')
        self.assertIn('obrigatorios', msg.lower())
        for campo in ('modelo', 'matricula', 'ano_compra'):
            self.assertIn(campo, msg)


# ---------------------------------------------------------------------------
# AC2 — modelo invalido (curto demais) → 400
# ---------------------------------------------------------------------------

class AC2_ModeloInvalido(TestCase):
    def test_modelo_um_caracter_retorna_400(self):
        resp = self.client.post(
            URL,
            data=json.dumps(_payload(modelo='A')),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn('modelo', resp.json()['message'].lower())


# ---------------------------------------------------------------------------
# AC3 — matricula invalida → 400
# ---------------------------------------------------------------------------

class AC3_MatriculaInvalida(TestCase):
    def test_matricula_curta_retorna_400(self):
        resp = self.client.post(
            URL,
            data=json.dumps(_payload(matricula='AB')),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn('matricula', resp.json()['message'].lower())


# ---------------------------------------------------------------------------
# AC4 — ano_compra invalido → 400
# ---------------------------------------------------------------------------

class AC4_AnoCompraInvalido(TestCase):
    def test_ano_nao_numerico_retorna_400(self):
        resp = self.client.post(
            URL,
            data=json.dumps(_payload(ano_compra='dois mil')),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_ano_anterior_a_1980_retorna_400(self):
        resp = self.client.post(
            URL,
            data=json.dumps(_payload(ano_compra=1979)),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn('1980', resp.json()['message'])

    def test_ano_futuro_retorna_400(self):
        futuro = date.today().year + 1
        resp = self.client.post(
            URL,
            data=json.dumps(_payload(ano_compra=futuro)),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)


# ---------------------------------------------------------------------------
# AC5 — Registo bem-sucedido → 201
# ---------------------------------------------------------------------------

class AC5_RegistoBemSucedido(TestCase):
    """Valid payload → 201; response shape must be stable for the client."""

    def test_retorna_201(self):
        resp = self.client.post(
            URL,
            data=json.dumps(_payload(matricula='AA-11-BB')),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 201)

    def test_resposta_contem_success_e_taxi(self):
        resp = self.client.post(
            URL,
            data=json.dumps(_payload(matricula='BB-22-CC')),
            content_type='application/json',
        )
        body = resp.json()
        self.assertTrue(body.get('success'))
        self.assertIn('taxi', body)

    def test_taxi_contem_campos_esperados(self):
        resp = self.client.post(
            URL,
            data=json.dumps(_payload(matricula='CC-33-DD')),
            content_type='application/json',
        )
        taxi = resp.json()['taxi']
        for campo in ('id_taxi', 'modelo', 'matricula', 'ano_compra'):
            self.assertIn(campo, taxi, msg=f"Campo '{campo}' em falta na resposta")
        self.assertEqual(taxi['modelo'], _VALID_PAYLOAD['modelo'])
        self.assertEqual(taxi['ano_compra'], _VALID_PAYLOAD['ano_compra'])

    def test_matricula_normalizada_para_maiusculas(self):
        resp = self.client.post(
            URL,
            data=json.dumps(_payload(matricula='dd-44-ee')),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()['taxi']['matricula'], 'DD-44-EE')

    def test_persistido_na_bd(self):
        self.client.post(
            URL,
            data=json.dumps(_payload(matricula='EE-55-FF')),
            content_type='application/json',
        )
        self.assertTrue(Taxi.objects.filter(matricula='EE-55-FF').exists())


# ---------------------------------------------------------------------------
# AC6 — Matricula duplicada → 409
# ---------------------------------------------------------------------------

class AC6_MatriculaDuplicada(TestCase):
    def test_segundo_registo_mesma_matricula_retorna_409(self):
        p = _payload(matricula='DU-PL-01')
        r1 = self.client.post(URL, data=json.dumps(p), content_type='application/json')
        self.assertEqual(r1.status_code, 201)

        p2 = _payload(matricula='DU-PL-01', modelo='Outro modelo')
        r2 = self.client.post(URL, data=json.dumps(p2), content_type='application/json')
        self.assertEqual(r2.status_code, 409)
        self.assertIn('message', r2.json())

    def test_apenas_um_registo_por_matricula(self):
        matricula = 'UN-IC-01'
        self.client.post(URL, data=json.dumps(_payload(matricula=matricula)), content_type='application/json')
        self.client.post(
            URL,
            data=json.dumps(_payload(matricula=matricula, modelo='X')),
            content_type='application/json',
        )
        self.assertEqual(Taxi.objects.filter(matricula=matricula).count(), 1)
