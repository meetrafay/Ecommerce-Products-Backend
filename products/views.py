from rest_framework import generics
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from .models import Product
from .serializers import ProductSerializer
from .filters import ProductFilter
from .permissions import IsInventoryManager

class ProductListCreateView(generics.ListCreateAPIView):
    """
    API endpoint for listing and creating products.
    Supports filtering and searching.
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsInventoryManager]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'sku']  # Fields to search on

class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API endpoint for retrieving, updating, and deleting a single product.
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsInventoryManager]