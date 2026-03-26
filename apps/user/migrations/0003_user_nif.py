from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_user_role_user_uid_alter_user_password'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='nif',
            field=models.CharField(blank=True, max_length=9, null=True, unique=True),
        ),
    ]
