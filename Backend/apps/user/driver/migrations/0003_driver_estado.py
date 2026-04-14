from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('driver', '0002_driver_validade_carta'),
    ]

    operations = [
        migrations.AddField(
            model_name='driver',
            name='estado',
            field=models.CharField(
                choices=[('disponivel', 'Disponível'), ('indisponivel', 'Indisponível')],
                default='indisponivel',
                max_length=20,
            ),
        ),
    ]
