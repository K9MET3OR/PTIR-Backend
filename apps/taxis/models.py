from django.db import models
from apps.users.models import User


class Motorista(models.Model):
    GENERO_CHOICES = [
        ('M', 'Masculino'),
        ('F', 'Feminino'),
        ('Outro', 'Outro'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='motorista',
    )
    ano_nascimento = models.IntegerField()
    genero = models.CharField(max_length=5, choices=GENERO_CHOICES)
    num_carta_conducao = models.CharField(max_length=50, unique=True)
    localidade = models.CharField(max_length=150)
    codigo_postal = models.CharField(max_length=10)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'motoristas'

    def __str__(self):
        return f"Motorista({self.user.username})"
