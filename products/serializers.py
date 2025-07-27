from rest_framework import serializers
from .models import Product

class ProductSerializer(serializers.ModelSerializer):
    """
    Serializer for the Product model.
    Handles serialization and validation of product data.
    """
    discounted_price = serializers.ReadOnlyField()
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'sku', 'price', 'quantity', 'last_updated', 'discounted_price']
        read_only_fields = ['id', 'last_updated', 'created_by', 'discounted_price']

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
    

class ShopifyWebhookSerializer(serializers.Serializer):
    """
    Serializer for Shopify inventory update webhook payload.
    Validates SKU and inventory quantity.
    """
    sku = serializers.CharField(max_length=50)
    inventory_quantity = serializers.IntegerField()

    def validate_sku(self, value):
        """Ensure SKU exists in the database."""
        if not Product.objects.filter(sku=value).exists():
            raise serializers.ValidationError("Product with this SKU does not exist.")
        return value

    def validate_inventory_quantity(self, value):
        """Ensure inventory quantity is non-negative."""
        if value < 0:
            raise serializers.ValidationError("Inventory quantity cannot be negative.")
        return value
    
    
class ProductDiscountSerializer(serializers.Serializer):
    """
    Serializer for adding or updating a product discount.
    """
    discount_percentage = serializers.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        min_value=0, 
        max_value=100,
        help_text="Discount percentage (0-100)"
    )