import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_user_nif'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[('admin', 'Admin'), ('motorista', 'Motorista'), ('cliente', 'Cliente')],
                default='cliente',
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name='Admin',
            fields=[
                (
                    'user_ptr',
                    models.OneToOneField(
                        auto_created=True,
                        db_column='user_id',
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        related_name='admin_profile',
                        serialize=False,
                        to='users.user',
                    ),
                ),
            ],
            options={
                'db_table': 'admins',
            },
            bases=('users.user',),
        ),
        migrations.CreateModel(
            name='Client',
            fields=[
                (
                    'user_ptr',
                    models.OneToOneField(
                        auto_created=True,
                        db_column='user_id',
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        related_name='client_profile',
                        serialize=False,
                        to='users.user',
                    ),
                ),
            ],
            options={
                'db_table': 'clients',
            },
            bases=('users.user',),
        ),
    ]
