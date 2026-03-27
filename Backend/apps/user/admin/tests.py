import json

import bcrypt
from django.test import TestCase

from apps.user.models import User


class AdminAuthTests(TestCase):
    def test_registo_admin_retorna_201(self):
        resp = self.client.post(
            '/auth/admin/registo',
            data=json.dumps(
                {
                    'username': 'admin_novo',
                    'email': 'admin_novo@example.com',
                    'password': 'Seguro123',
                    'name': 'Admin Novo',
                    'nif': '123456789',
                }
            ),
            content_type='application/json',
        )

        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertEqual(body['user']['role'], 'admin')

    def test_login_admin_retorna_token(self):
        pwd = bcrypt.hashpw('Senha123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        User.objects.create(
            username='admin_login',
            email='admin_login@example.com',
            password=pwd,
            name='Admin Login',
            role='admin',
            nif='123456789',
        )

        resp = self.client.post(
            '/auth/admin/login',
            data=json.dumps({'nif': '123456789', 'password': 'Senha123'}),
            content_type='application/json',
        )

        self.assertEqual(resp.status_code, 200)
        self.assertIn('token', resp.json())
