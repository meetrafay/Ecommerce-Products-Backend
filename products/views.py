import numpy as np
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.conf import settings
from decouple import config
import hmac
import hashlib
import base64

from sentence_transformers import SentenceTransformer
from .models import Product
from .serializers import ProductSerializer, ShopifyWebhookSerializer
from .filters import ProductFilter
from .permissions import IsInventoryManager
from django.core.cache import cache
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

    def verify_webhook(self, data, hmac_header):
        """Verify Shopify webhook using HMAC signature."""
        secret = config('SHOPIFY_WEBHOOK_SECRET', default='')
        digest = hmac.new(
            secret.encode('utf-8'),
            data,
            hashlib.sha256
        ).digest()
        computed_hmac = base64.b64encode(digest).decode('utf-8')
        return hmac.compare_digest(computed_hmac, hmac_header)

    def post(self, request, *args, **kwargs):
        """Handle Shopify inventory update webhook."""
        # Verify webhook signature
        hmac_header = request.META.get('HTTP_X_SHOPIFY_HMAC_SHA256', '')
        if not self.verify_webhook(request.body, hmac_header):
            return Response({'error': 'Invalid webhook signature'}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = ShopifyWebhookSerializer(data=request.data)
        if serializer.is_valid():
            sku = serializer.validated_data['sku']
            inventory_quantity = serializer.validated_data['inventory_quantity']
            product = Product.objects.get(sku=sku)
            product.quantity = inventory_quantity
            product.save()
            return Response({'status': 'Inventory updated successfully'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class ProductSearchView(generics.ListAPIView):
    """
    API endpoint for semantic product search using Sentence-Transformers.
    Ranks results by similarity to the query (?q=...).
    """
    serializer_class = ProductSerializer
    permission_classes = [IsInventoryManager]

    def get_queryset(self):
        query = self.request.query_params.get('q', '')
        if not query:
            return Product.objects.all()

        # Load Sentence-Transformer model
        model = SentenceTransformer('all-MiniLM-L6-v2')
        query_embedding = model.encode(query)

        # Get all products and their embeddings
        products = Product.objects.all()
        results = []
        for product in products:
            # Try to get embedding from cache
            cache_key = f"product_embedding_{product.sku}"
            cached_embedding = cache.get(cache_key)
            if cached_embedding:
                product_embedding = np.frombuffer(cached_embedding, dtype=np.float32)
            else:
                product_embedding = product.get_embedding()
                if product_embedding is None:
                    product_embedding = model.encode(product.name)
                    product.set_embedding(product_embedding)
                    product.save()
                    cache.set(cache_key, product_embedding.tobytes(), timeout=None)

            # Calculate cosine similarity
            similarity = np.dot(query_embedding, product_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(product_embedding)
            )
            results.append((product, similarity))

        # Sort by similarity (descending) and filter out low scores
        results.sort(key=lambda x: x[1], reverse=True)
        return [product for product, similarity in results if similarity > 0.1]  # Threshold for relevance