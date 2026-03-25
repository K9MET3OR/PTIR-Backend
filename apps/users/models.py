from django.db import models
import uuid

class User(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255, null=True, blank=True)  # Make password optional for Firebase auth
    name = models.CharField(max_length=100)

    uid = models.CharField(max_length=255, unique=True, null=True, blank=True)  # Firebase UID
    role = models.CharField(max_length=20, choices=[('gestor', 'Gestor'), ('motorista', 'Motorista'), ('cliente', 'Cliente')], default='cliente')

    mobile = models.CharField(max_length=20, null=True, blank=True)
    address = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username