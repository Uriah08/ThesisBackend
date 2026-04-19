from rest_framework import serializers

from retails.serializers import RetailShopSerializer
from .models import FarmProductionModel


class FarmProductionSerializer(serializers.ModelSerializer):
    retail_detail = RetailShopSerializer(source='retail', read_only=True)
    class Meta:
        model = FarmProductionModel
        fields = [
            'id',
            'farm',
            'title',
            'notes',
            'satisfaction',
            'total',
            'quantity',
            'landing',
            'retail',
            'retail_detail',
            'created_at',
        ]