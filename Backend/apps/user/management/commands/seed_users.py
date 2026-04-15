from django.core.management.base import BaseCommand
from firebase_admin import auth

import apps.user.firebase_init  # garante que o Firebase está inicializado
from apps.user.models import User


SEED_USERS = [
    {
        'email':    'admin@admin.com',
        'password': '123456',
        'username': 'admin',
        'name':     'Administrador',
        'role':     'admin',
    },
    {
        'email':    'motorista@motorista.com',
        'password': '123456',
        'username': 'motorista',
        'name':     'Motorista Teste',
        'role':     'motorista',
    },
    {
        'email':    'cliente@cliente.com',
        'password': '123456',
        'username': 'cliente',
        'name':     'Cliente Teste',
        'role':     'cliente',
    },
]


class Command(BaseCommand):
    help = 'Cria utilizadores de teste (um por role) no Firebase e na DB'

    def handle(self, *args, **kwargs):
        for u in SEED_USERS:
            # Criar ou reutilizar no Firebase
            try:
                fb_user = auth.get_user_by_email(u['email'])
                self.stdout.write(f"  [firebase] {u['email']} já existe no Firebase")
                # Atualizar a senha para garantir que corresponde
                try:
                    auth.update_user(
                        fb_user.uid,
                        password=u['password'],
                    )
                    self.stdout.write(f"  [firebase] senha atualizada para {u['email']}")
                except Exception as e:
                    self.stdout.write(f"  [firebase] erro ao atualizar senha: {e}")
            except auth.UserNotFoundError:
                fb_user = auth.create_user(
                    email=u['email'],
                    password=u['password'],
                    display_name=u['name'],
                )
                self.stdout.write(f"  [firebase] {u['email']} criado")

            # Verificar se já existe na DB
            existing_user = User.objects.filter(email=u['email']).first()
            if existing_user:
                # Atualizar UID se necessário
                if existing_user.uid != fb_user.uid:
                    existing_user.uid = fb_user.uid
                    existing_user.save()
                self.stdout.write(f"  [skip] {u['email']} já existe na DB")
                continue

            # Criar na DB
            User.objects.create(
                uid=fb_user.uid,
                email=u['email'],
                username=u['username'],
                name=u['name'],
                role=u['role'],
            )
            self.stdout.write(self.style.SUCCESS(f"  [db] {u['role']} '{u['username']}' criado"))

        self.stdout.write(self.style.SUCCESS('\nSeed concluído!'))
