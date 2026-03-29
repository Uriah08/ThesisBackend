from rest_framework import serializers
from .models import FarmProductionModel

class FarmProductionSerializer(serializers.ModelSerializer):
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
            'created_at',
        ]