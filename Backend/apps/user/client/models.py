from django.core.exceptions import ValidationError
from django.db import models

from ..models import User


class Client(User):
    user_ptr = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        parent_link=True,
        primary_key=True,
        db_column='user_id',
        related_name='client_profile',
    )

    genero = models.CharField(
        max_length=20,
        choices=[
            ('masculino', 'Masculino'),
            ('feminino', 'Feminino'),
        ],
        null=True,
        blank=True,
    )

    class Meta:
        db_table = 'clients'

    def clean(self):
        if self.role != 'cliente':
            raise ValidationError("Client tem de ter role='cliente'.")

    def save(self, *args, **kwargs):
        self.role = 'cliente'
        return super().save(*args, **kwargs)