from django.db import models
from apps.user.models import User


class Driver(User):
    GENERO_CHOICES = [
        ('M', 'Masculino'),
        ('F', 'Feminino'),
        ('Outro', 'Outro'),
    ]

    user_ptr = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        parent_link=True,
        primary_key=True,
        db_column='user_id',
        related_name='driver',
    )
    ano_nascimento = models.IntegerField()
    genero = models.CharField(max_length=5, choices=GENERO_CHOICES)
    num_carta_conducao = models.CharField(max_length=50, unique=True)
    localidade = models.CharField(max_length=150)
    codigo_postal = models.CharField(max_length=10)

    class Meta:
        db_table = 'motoristas'

    def __str__(self):
        return f"Driver({self.username})"
