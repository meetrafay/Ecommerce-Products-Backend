import numpy as np
from authentication.models import Profile
from django.db import models

class Product(models.Model):
    """
    Model representing a product in the inventory.
    
    Attributes:
        name (str): The name of the product.
        sku (str): Unique Stock Keeping Unit identifier.
        price (Decimal): Price of the product.
        quantity (int): Available inventory quantity.
        last_updated (datetime): Timestamp of the last update.
    """
    i_profile = models.ForeignKey(
        Profile,
        on_delete=models.SET_NULL,
        null=True, help_text="User profile that created the product")
    name = models.CharField(max_length=255, help_text="Name of the product")
    sku = models.CharField(max_length=50, unique=True, help_text="Unique SKU for the product")
    discount_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.00, 
        help_text="Discount percentage (0-100)"
    )
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price of the product")
    quantity = models.PositiveIntegerField(default=0, help_text="Available quantity in inventory")
    last_updated = models.DateTimeField(auto_now=True, help_text="Last updated timestamp")
    embedding = models.BinaryField(null=True, blank=True, help_text="Semantic embedding of the product name")

    class Meta:
        ordering = ['name']
        verbose_name = 'Product'
        verbose_name_plural = 'Products'

    def __str__(self):
        return f"{self.name} ({self.sku})"
    
    def set_embedding(self, embedding):
        """Store numpy array as binary in embedding field."""
        self.embedding = np.array(embedding, dtype=np.float32).tobytes()

    def get_embedding(self):
        """Retrieve embedding as numpy array."""
        if self.embedding:
            return np.frombuffer(self.embedding, dtype=np.float32)
        return None
    
    @property
    def discounted_price(self):
        """Calculate the discounted price based on discount_percentage."""
        return self.price * (1 - self.discount_percentage / 100)
    
    
class StockHistory(models.Model):
    """
    Model to track historical stock changes for a product.
    
    Attributes:
        product (Product): The related product.
        quantity (int): The quantity at the time of the update.
        timestamp (datetime): When the stock change occurred.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_history')
    quantity = models.PositiveIntegerField(help_text="Quantity at the time of update")
    timestamp = models.DateTimeField(auto_now_add=True, help_text="Timestamp of the stock change")

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Stock History'
        verbose_name_plural = 'Stock Histories'

    def __str__(self):
        return f"{self.product.sku} - {self.quantity} units at {self.timestamp}"