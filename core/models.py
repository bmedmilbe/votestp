
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    USER_TYPES = (
        ('admin', 'Administrador'),
        ('agent', 'Agent'),
        ('citizen', 'Elector'),
    )
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='citizen')
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    