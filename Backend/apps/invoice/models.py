from django.db import models


class Invoice(models.Model):
    trip = models.OneToOneField(
        "trip.Trip",
        on_delete=models.CASCADE,
        related_name="invoice"
    )

    n_fatura = models.PositiveIntegerField()
    ano = models.PositiveIntegerField()
    data = models.DateTimeField()

    price = models.DecimalField(max_digits=8, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["n_fatura", "ano"],
                name="unique_invoice_number_per_year"
            )
        ]

    def __str__(self):
        return f"Invoice {self.n_fatura}/{self.ano}"