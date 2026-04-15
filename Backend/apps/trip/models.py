from django.db import models
import uuid
# Create your models here.


class Trip(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("in_progress", "In Progress"),
        ("finished", "Finished"),
        ("cancelled", "Cancelled"),
    ]

    CONFORTO_CHOICES = [
        ("Standard", "Standard"),
        ("Conforto", "Conforto"),
        ("Premium", "Premium"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    client = models.ForeignKey(
        "client.Client",
        on_delete=models.CASCADE,
        related_name="trips",
    )

    driver = models.ForeignKey(
        "driver.Driver",
        on_delete=models.CASCADE,
        related_name="trips",
        null=True,
        blank=True,
    )
    taxi = models.ForeignKey(
        "taxi.Taxi",
        on_delete=models.CASCADE,
        related_name="trips",
        null=True,
        blank=True,
    )
    shift = models.ForeignKey(
        "shift.Shift",
        on_delete=models.CASCADE,
        related_name="trips",
        null=True,
        blank=True
    )

    start_location = models.CharField(max_length=255)
    end_location = models.CharField(max_length=255)

    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)

    n_people = models.PositiveIntegerField()
    n_kms = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    nivel_conforto = models.CharField(
        max_length=20,
        choices=CONFORTO_CHOICES,
        default="Standard",
    )

    status_trip = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )


    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Trip #{self.id} - {self.client}"