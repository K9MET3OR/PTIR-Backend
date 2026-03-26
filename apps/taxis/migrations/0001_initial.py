import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('users', '0002_user_role_user_uid_alter_user_password'),
    ]

    operations = [
        migrations.CreateModel(
            name='Motorista',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ano_nascimento', models.IntegerField()),
                ('genero', models.CharField(choices=[('M', 'Masculino'), ('F', 'Feminino'), ('Outro', 'Outro')], max_length=5)),
                ('num_carta_conducao', models.CharField(max_length=50, unique=True)),
                ('localidade', models.CharField(max_length=150)),
                ('codigo_postal', models.CharField(max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='motorista',
                    to='users.user',
                )),
            ],
            options={
                'db_table': 'motoristas',
            },
        ),
    ]
