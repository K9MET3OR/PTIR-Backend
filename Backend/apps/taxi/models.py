import uuid
from django.db import models


class Taxi(models.Model):
    """
    Veiculo da frota (taxi).

    id_taxi: identificador unico do taxi (UUID).
    """

    ESTADO_CHOICES = [
        ('disponivel', 'Disponível'),
        ('indisponivel', 'Indisponível'),
        ('ocupado', 'Ocupado'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    modelo = models.CharField(max_length=100)
    matricula = models.CharField(max_length=20, unique=True)
    ano_compra = models.PositiveIntegerField()
    consumo_medio = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    marca = models.CharField(max_length=50)
    tipo_motor = models.CharField(max_length=50, choices=[('Gasolina', 'Gasolina'), ('Diesel', 'Diesel'), ('Elétrico', 'Elétrico'), ('Híbrido', 'Híbrido')], default='Gasolina')
    nivel_conforto = models.CharField(max_length=20, choices=[('Standard', 'Standard'), ('Conforto', 'Conforto'), ('Premium', 'Premium')])
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='disponivel')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.matricula} ({self.modelo})"
