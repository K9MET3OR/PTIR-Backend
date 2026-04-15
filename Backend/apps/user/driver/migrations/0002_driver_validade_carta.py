from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('driver', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='driver',
            name='validade_carta',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='driver',
            name='localidade',
            field=models.CharField(blank=True, default='', max_length=150),
        ),
        migrations.AlterField(
            model_name='driver',
            name='codigo_postal',
            field=models.CharField(blank=True, default='', max_length=10),
        ),
    ]
