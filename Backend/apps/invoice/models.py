from django.db import models


class Invoice(models.Model):
    trip = models.OneToOneField(
        "trip.Trip",
        on_delete=models.CASCADE,
        related_name="invoice"
    )
    n_fatura = models.CharField(max_length=50, unique=True)
    data = models.DateTimeField()
    price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Invoice {self.n_fatura}"