from django.core.exceptions import ValidationError
from django.db import models

from ..models import User


class Admin(User):
    user_ptr = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        parent_link=True,
        primary_key=True,
        db_column='user_id',
        related_name='admin_profile',
    )

    class Meta:
        db_table = 'admins'

    def clean(self):
        if self.role != 'admin':
            raise ValidationError("Admin tem de ter role='admin'.")

    def save(self, *args, **kwargs):
        self.role = 'admin'
        return super().save(*args, **kwargs)
