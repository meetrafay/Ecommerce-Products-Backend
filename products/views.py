from datetime import timedelta
from django.utils import timezone
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
from .models import Product, StockHistory
from .serializers import ProductDiscountSerializer, ProductSerializer, ShopifyWebhookSerializer
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
        # hmac_header = request.META.get('HTTP_X_SHOPIFY_HMAC_SHA256', '')
        # if not self.verify_webhook(request.body, hmac_header):
        #     return Response({'error': 'Invalid webhook signature'}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = ShopifyWebhookSerializer(data=request.data)
        if serializer.is_valid():
            sku = serializer.validated_data['sku']
            inventory_quantity = serializer.validated_data['inventory_quantity']
            product = Product.objects.get(sku=sku)
            StockHistory.objects.create(product=product, quantity=inventory_quantity)
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
    # permission_classes = [IsInventoryManager]

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
    
    

# class ProductInsightsView(APIView):
#     """
#     API endpoint for inventory insights.
#     Returns basic statistics and trending products based on stock changes.
#     """
#     # permission_classes = [IsInventoryManager]

#     def get(self, request, *args, **kwargs):
#         cache_key = 'product_insights'
#         cached_data = cache.get(cache_key)
#         if cached_data:
#             return Response(cached_data)

#         # Basic statistics
#         total_products = Product.objects.count()
#         low_stock_threshold = 10
#         low_stock_products = Product.objects.filter(quantity__lt=low_stock_threshold).count()
#         low_stock_percentage = (low_stock_products / total_products * 100) if total_products > 0 else 0

#         # Trending products (quantity decreased by >20% in last 7 days)
#         seven_days_ago = timezone.now() - timedelta(days=7)
#         trending_products = []
#         products = Product.objects.all()
#         for product in products:
#             history = product.stock_history.filter(timestamp__gte=seven_days_ago).order_by('timestamp')
#             if history.count() >= 2:
#                 oldest = history.first().quantity
#                 newest = history.last().quantity
#                 if oldest > 0:
#                     percentage_change = ((newest - oldest) / oldest) * 100
#                     if percentage_change <= -20:  # Significant decrease
#                         trending_products.append({
#                             'name': product.name,
#                             'sku': product.sku,
#                             'quantity_change': newest - oldest,
#                             'percentage_change': round(percentage_change, 2)
#                         })

#         response_data = {
#             'statistics': {
#                 'total_products': total_products,
#                 'low_stock_products': low_stock_products,
#                 'low_stock_percentage': round(low_stock_percentage, 2)
#             },
#             'trending_products': trending_products
#         }

#         # Cache for 1 hour
#         cache.set(cache_key, response_data, timeout=3600)
#         return Response(response_data)


class ProductInsightsView(generics.GenericAPIView):
    """
    API endpoint for product insights, including low-stock stats and trending products.
    """
    serializer_class = ProductSerializer
    # permission_classes = [IsInventoryManager]

    def get(self, request, *args, **kwargs):
        cache_key = 'product_insights'
        # cached_data = cache.get(cache_key)
        # if cached_data:
        #     return Response(cached_data)

        # Basic statistics
        total_products = Product.objects.count()
        low_stock_threshold = 10
        low_stock_products = Product.objects.filter(quantity__lt=low_stock_threshold).count()
        low_stock_percentage = (low_stock_products / total_products * 100) if total_products > 0 else 0

        # Trending products based on stock changes
        trending_products = self.get_trending_products()

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

    def get_trending_products(self):
        """
        Identify trending products based on recent stock changes (last 7 days).
        Uses percentage change in stock to rank products.
        """
        from sklearn.preprocessing import StandardScaler
        from sklearn.cluster import KMeans
        print("step 01")
        # Get stock history from the last 7 days
        time_threshold = timezone.now() - timedelta(days=7)
        products = Product.objects.prefetch_related('stock_history').all()
        trends = []

        for product in products:
            history = product.stock_history.filter(timestamp__gte=time_threshold).order_by('timestamp')
            if history.count() < 2:
                continue

            # Calculate percentage change in stock
            first_record = history.first().quantity
            last_record = history.last().quantity
            if first_record == 0:
                continue
            percentage_change = ((last_record - first_record) / first_record) * 100
            trends.append({
                'product': product,
                'percentage_change': percentage_change,
                'quantity_change': last_record - first_record
            })

        if not trends:
            return []

        # Feature scaling for clustering
        X = [[t['percentage_change'], t['quantity_change']] for t in trends]
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Cluster products to identify trending ones (e.g., significant stock depletion)
        kmeans = KMeans(n_clusters=3, random_state=42)
        labels = kmeans.fit_predict(X_scaled)

        # Assume cluster with largest negative percentage change is "trending"
        cluster_changes = [[] for _ in range(3)]
        print("====", cluster_changes)
        for i, trend in enumerate(trends):
            cluster_changes[labels[i]].append(trend)

        trending_cluster = max(cluster_changes, key=lambda c: -sum(t['percentage_change'] for t in c) if c else 0)
        trending_products = [t['product'] for t in trending_cluster if t['percentage_change'] < -20]  # Threshold for significant depletion

        return trending_products[:5]  # Return top 5 trending products

    
class ProductDiscountView(generics.GenericAPIView):
    """
    API endpoint to add or update a discount percentage for a product.
    """
    serializer_class = ProductDiscountSerializer
    permission_classes = [IsInventoryManager]

    def post(self, request, pk, *args, **kwargs):
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
            cache_key = f"product_embedding_{product.sku}"
            cache.delete(cache_key)
            cache_key_insights = 'product_insights'
            cache.delete(cache_key_insights)
            cache_key_trends = 'trending_products'
            cache.delete(cache_key_trends)

            # Return updated product
            return Response(ProductSerializer(product).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)