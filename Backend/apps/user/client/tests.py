import json

import bcrypt
from django.test import TestCase

from apps.user.models import User


class ClientAuthTests(TestCase):
    def test_registo_client_retorna_201(self):
        resp = self.client.post(
            '/auth/client/registo',
            data=json.dumps(
                {
                    'username': 'cliente_novo',
                    'email': 'cliente_novo@example.com',
                    'password': 'Seguro123',
                    'name': 'Cliente Novo',
                    'nif': '123456789',
                }
            ),
            content_type='application/json',
        )

        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertEqual(body['user']['role'], 'cliente')

    def test_login_client_retorna_token(self):
        pwd = bcrypt.hashpw('Senha123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        User.objects.create(
            username='cliente_login',
            email='cliente_login@example.com',
            password=pwd,
            name='Cliente Login',
            role='cliente',
            nif='123456789',
        )

        resp = self.client.post(
            '/auth/client/login',
            data=json.dumps({'nif': '123456789', 'password': 'Senha123'}),
            content_type='application/json',
        )

        self.assertEqual(resp.status_code, 200)
        self.assertIn('token', resp.json())
