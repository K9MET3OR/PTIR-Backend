from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('taxi', '0006_taxi_consumo_medio'),
    ]

    operations = [
        migrations.AddField(
            model_name='taxi',
            name='estado',
            field=models.CharField(
                choices=[
                    ('disponivel', 'Disponível'),
                    ('indisponivel', 'Indisponível'),
                    ('ocupado', 'Ocupado'),
                ],
                default='disponivel',
                max_length=20,
            ),
        ),
    ]
