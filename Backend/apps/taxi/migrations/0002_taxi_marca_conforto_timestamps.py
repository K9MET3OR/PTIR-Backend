import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('taxi', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='taxi',
            name='marca',
            field=models.CharField(blank=True, default='', max_length=50),
        ),
        migrations.AddField(
            model_name='taxi',
            name='nivel_conforto',
            field=models.CharField(
                choices=[('baixo', 'Baixo'), ('medio', 'Medio'), ('alto', 'Alto')],
                default='medio',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='taxi',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='taxi',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
