import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Taxi',
            fields=[
                (
                    'id_taxi',
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ('modelo', models.CharField(max_length=100)),
                ('matricula', models.CharField(max_length=20, unique=True)),
                ('ano_compra', models.PositiveIntegerField()),
            ],
            options={
                'db_table': 'taxis',
            },
        ),
    ]
