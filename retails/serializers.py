from rest_framework import serializers
from .models import RetailShop


class RetailShopSerializer(serializers.ModelSerializer):
    created_at = serializers.SerializerMethodField()

    def get_created_at(self, obj):
        value = obj.created_at
        if hasattr(value, 'date'):
            return value.date().isoformat()
        return str(value)

    class Meta:
        model = RetailShop
        fields = ['id', 'farm', 'store_name', 'location', 'contact', 'created_at']
        read_only_fields = ['id', 'farm', 'created_at']