from typing import List
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend

from .models import Product, StockHistory
from .serializers import ProductDiscountSerializer, ProductSerializer, ShopifyWebhookSerializer
from .filters import ProductFilter
from .permissions import IsInventoryManager
from django.core.cache import cache
from .utils import verify_shopify_webhook, compute_similarity, compute_trending_products



class ProductListCreateView(generics.ListCreateAPIView):
    """
    API endpoint for listing and creating products.
    Supports filtering and searching.
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    # permission_classes = [IsInventoryManager]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'sku']  # Fields to search on

    def perform_create(self, serializer: ProductSerializer) -> None:
        """Set the created_by field to the authenticated user's profile."""
        serializer.save(i_profile=self.request.user.profile)

class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API endpoint for retrieving, updating, and deleting a single product.
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    # permission_classes = [IsInventoryManager]


class ShopifyInventoryWebhookView(APIView):
    """
    Webhook endpoint for Shopify inventory updates.
    Validates payload and updates product inventory quantity.
    """
    permission_classes = []  # No authentication required for webhooks

    def post(self, request, *args, **kwargs) -> Response:
        """Handle Shopify inventory update webhook."""
        hmac_header = request.META.get('HTTP_X_SHOPIFY_HMAC_SHA256', '')
        if not verify_shopify_webhook(request.body, hmac_header):
            return Response({'error': 'Invalid webhook signature'}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = ShopifyWebhookSerializer(data=request.data)
        if serializer.is_valid():
            sku = serializer.validated_data['sku']
            inventory_quantity = serializer.validated_data['inventory_quantity']
            try:
                product = Product.objects.get(sku=sku)
                StockHistory.objects.create(product=product, quantity=inventory_quantity)
                product.quantity = inventory_quantity
                product.save()
                return Response({'status': 'Inventory updated successfully'}, status=status.HTTP_200_OK)
            except Product.DoesNotExist:
                return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class ProductSearchView(generics.ListAPIView):
    """
    API endpoint for semantic product search using Sentence-Transformers.
    Ranks results by similarity to the query (?q=...).
    """
    serializer_class = ProductSerializer
    # permission_classes = [IsInventoryManager]

    def get_queryset(self) -> List[Product]:
        """Return products ranked by semantic similarity to the query."""
        query = self.request.query_params.get('q', '')
        products = Product.objects.all()
        return compute_similarity(query, products)


class ProductInsightsView(generics.GenericAPIView):
    """
    API endpoint for product insights, including low-stock stats and trending products.
    """
    serializer_class = ProductSerializer
    # permission_classes = [IsInventoryManager]

    def get(self, request, *args, **kwargs) -> Response:
        """Return cached or computed product insights."""
        cache_key = 'product_insights'
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)

        total_products = Product.objects.count()
        low_stock_threshold = 10
        low_stock_products = Product.objects.filter(quantity__lt=low_stock_threshold).count()
        low_stock_percentage = (low_stock_products / total_products * 100) if total_products > 0 else 0

        trending_products = compute_trending_products(Product.objects.prefetch_related('stock_history').all())

        data = {
            'statistics': {
                'total_products': total_products,
                'low_stock_products': low_stock_products,
                'low_stock_percentage': round(low_stock_percentage, 2),
            },
            'trending_products': ProductSerializer(trending_products, many=True).data
        }

        cache.set(cache_key, data, timeout=3600)  # Cache for 1 hour
        return Response(data)

    
class ProductDiscountView(generics.GenericAPIView):
    """
    API endpoint to add or update a discount percentage for a product.
    """
    serializer_class = ProductDiscountSerializer
    permission_classes = [IsInventoryManager]

    def post(self, request, pk: int, *args, **kwargs) -> Response:
        """
        Set or update the discount percentage for a product.
        """
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            product.discount_percentage = serializer.validated_data['discount_percentage']
            product.save()

            # Clear cached product data
            cache.delete(f"product_embedding_{product.sku}")
            cache.delete('product_insights')
            cache.delete('trending_products')

            return Response(ProductSerializer(product).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)