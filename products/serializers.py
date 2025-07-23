from rest_framework import serializers
from .models import Product

class ProductSerializer(serializers.ModelSerializer):
    """
    Serializer for the Product model.
    Handles serialization and validation of product data.
    """
    class Meta:
        model = Product
        fields = ['id', 'name', 'sku', 'price', 'quantity', 'last_updated']
        read_only_fields = ['last_updated']

    def validate_sku(self, value):
        """Ensure SKU is unique and not empty."""
        if not value.strip():
            raise serializers.ValidationError("SKU cannot be empty.")
        return value

    def validate_price(self, value):
        """Ensure price is non-negative."""
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        return value

    def validate_quantity(self, value):
        """Ensure quantity is non-negative."""
        if value < 0:
            raise serializers.ValidationError("Quantity cannot be negative.")
        return value