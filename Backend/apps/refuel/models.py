from django.db import models


class Refuel(models.Model):
    TIPO_CHOICES = [
        ("gasolina", "Gasolina"),
        ("gasoleo", "Gasóleo"),
        ("eletrico", "Elétrico"),
    ]

    taxi = models.ForeignKey(
        "taxi.Taxi",
        on_delete=models.CASCADE,
        related_name="refuels"
    )
    shift = models.ForeignKey(
        "shift.Shift",
        on_delete=models.CASCADE,
        related_name="refuels"
    )
    data_inicio = models.DateTimeField()
    data_fim = models.DateTimeField(null=True, blank=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    kms_previos = models.DecimalField(max_digits=10, decimal_places=2)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    quantidade = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Refuel {self.id} - Taxi {self.taxi_id}"