import uuid
from django.db import models


class Taxi(models.Model):
    """
    Veiculo da frota (taxi).

    id_taxi: identificador unico do taxi (UUID).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    modelo = models.CharField(max_length=100)
    matricula = models.CharField(max_length=20, unique=True)
    ano_compra = models.PositiveIntegerField()
    marca = models.CharField(max_length=50)
    nivel_conforto = models.CharField(max_length=20, choices=[('baixo', 'Baixo'), ('medio', 'Medio'), ('alto', 'Alto')])

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.matricula} ({self.modelo})"
