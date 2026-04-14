from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('taxi', '0007_taxi_estado'),
    ]

    operations = [
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
