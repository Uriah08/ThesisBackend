from django.db import models
from django.utils import timezone
from farms.models import FarmModel


class RetailShop(models.Model):
    farm = models.ForeignKey(
        FarmModel,
        related_name='retail_shops',
        on_delete=models.CASCADE
    )
    store_name = models.CharField(max_length=132)
    location = models.CharField(max_length=255)
    contact = models.CharField(max_length=32, blank=True, null=True)
    created_at = models.DateField(default=timezone.now)

    def __str__(self):
        return f"{self.store_name} ({self.farm.name})"