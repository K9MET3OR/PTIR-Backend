from django.db import models


class Shift(models.Model):
    driver = models.ForeignKey(
        "driver.Driver",
        on_delete=models.CASCADE,
        related_name="shifts"
    )
    taxi = models.ForeignKey(
        "taxi.Taxi",
        on_delete=models.CASCADE,
        related_name="shifts"
    )
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    status_shift = models.CharField(max_length=20, default="active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Shift {self.id} - Driver {self.driver_id}"