# Generated migration to add estado field to Taxi model

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
                choices=[('disponivel', 'Disponível'), ('indisponivel', 'Indisponível'), ('ocupado', 'Ocupado')],
                default='disponivel',
                max_length=20
            ),
        ),
        migrations.AddField(
            model_name='taxi',
            name='latitude',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
        migrations.AddField(
            model_name='taxi',
            name='longitude',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
    ]
