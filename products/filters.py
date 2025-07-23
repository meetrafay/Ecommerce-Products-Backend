from django_filters import rest_framework as filters
from .models import Product

class ProductFilter(filters.FilterSet):
    """
    Filter class for Product model to support filtering and searching.
    """
    price_min = filters.NumberFilter(field_name='price', lookup_expr='gte')
    price_max = filters.NumberFilter(field_name='price', lookup_expr='lte')
    quantity_min = filters.NumberFilter(field_name='quantity', lookup_expr='gte')
    quantity_max = filters.NumberFilter(field_name='quantity', lookup_expr='lte')

    class Meta:
        model = Product
        fields = {
            'sku': ['exact', 'icontains'],
            'name': ['exact', 'icontains'],
            'price': ['exact'],
            'quantity': ['exact'],
        }