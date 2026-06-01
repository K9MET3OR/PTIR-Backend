import uuid
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator


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
    tipo_motor = models.CharField(
        max_length=50,
        choices=[('Combustão', 'Combustão'), ('Elétrico', 'Elétrico')],
        default='Combustão'
    )
    nivel_conforto = models.CharField(
        max_length=20,
        choices=[('Básico', 'Básico'), ('Luxuoso', 'Luxuoso')]
    )
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='disponivel')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.matricula} ({self.modelo})"


class PricingConfig(models.Model):
    """
    Configuração de preços do serviço de táxi.

    Usada na User Story 3:
    - preço por minuto para táxis Básico e Luxuoso;
    - acréscimo percentual noturno entre as 21h e as 6h.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    preco_basico_minuto = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.25"),
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    preco_luxuoso_minuto = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.40"),
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    agravamento_noturno_percentual = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("20.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def get_config(cls):
        config = cls.objects.first()

        if config:
            return config

        return cls.objects.create(
            preco_basico_minuto=Decimal("0.25"),
            preco_luxuoso_minuto=Decimal("0.40"),
            agravamento_noturno_percentual=Decimal("20.00"),
        )

    def __str__(self):
        return (
            f"Preços: Básico {self.preco_basico_minuto}€/min, "
            f"Luxuoso {self.preco_luxuoso_minuto}€/min, "
            f"Noite +{self.agravamento_noturno_percentual}%"
        )