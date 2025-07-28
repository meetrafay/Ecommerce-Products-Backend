from typing import List, Tuple, Optional
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from decouple import config
import hmac
import hashlib
import base64
from .models import Product

def verify_shopify_webhook(data: bytes, hmac_header: str) -> bool:
    """
    Verify Shopify webhook using HMAC signature.

    Args:
        data (bytes): Raw request body.
        hmac_header (str): HMAC signature from request headers.

    Returns:
        bool: True if the signature is valid, False otherwise.
    """
    secret = config('SHOPIFY_WEBHOOK_SECRET', default='')
    digest = hmac.new(
        secret.encode('utf-8'),
        data,
        hashlib.sha256
    ).digest()
    computed_hmac = base64.b64encode(digest).decode('utf-8')
    return hmac.compare_digest(computed_hmac, hmac_header)

def generate_product_embedding(product: Product, model: SentenceTransformer) -> np.ndarray:
    """
    Generate or retrieve a product's embedding, caching the result.

    Args:
        product (Product): The product instance.
        model (SentenceTransformer): The Sentence-Transformer model.

    Returns:
        np.ndarray: The product's embedding.
    """
    cache_key = f"product_embedding_{product.sku}"
    cached_embedding = cache.get(cache_key)
    if cached_embedding:
        return np.frombuffer(cached_embedding, dtype=np.float32)

    product_embedding = product.get_embedding()
    if product_embedding is None:
        product_embedding = model.encode(product.name)
        product.set_embedding(product_embedding)
        product.save()
        cache.set(cache_key, product_embedding.tobytes(), timeout=None)
    
    return product_embedding

def compute_similarity(query: str, products: List[Product], threshold: float = 0.1) -> List[Product]:
    """
    Compute semantic similarity between a query and products using Sentence-Transformers.

    Args:
        query (str): The search query.
        products (List[Product]): List of products to search.
        threshold (float): Minimum similarity score for relevance.

    Returns:
        List[Product]: Ordered list of relevant products.
    """
    if not query:
        return products

    model = SentenceTransformer('all-MiniLM-L6-v2')
    query_embedding = model.encode(query)
    results = []

    for product in products:
        product_embedding = generate_product_embedding(product, model)
        similarity = np.dot(query_embedding, product_embedding) / (
            np.linalg.norm(query_embedding) * np.linalg.norm(product_embedding)
        )
        if similarity > threshold:
            results.append((product, similarity))

    results.sort(key=lambda x: x[1], reverse=True)
    return [product for product, _ in results]

def compute_trending_products(products: List[Product], days: int = 7, threshold: float = -20) -> List[Product]:
    """
    Identify trending products based on stock changes over a given period.

    Args:
        products (List[Product]): List of products to analyze.
        days (int): Number of days to consider for stock changes.
        threshold (float): Minimum percentage change for trending products.

    Returns:
        List[Product]: Up to 5 trending products with significant stock depletion.
    """
    time_threshold = timezone.now() - timedelta(days=days)
    trends = []

    for product in products:
        history = product.stock_history.filter(timestamp__gte=time_threshold).order_by('timestamp')
        if history.count() < 2:
            continue

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

    # Cluster products
    kmeans = KMeans(n_clusters=3, random_state=42)
    labels = kmeans.fit_predict(X_scaled)

    # Group by cluster
    cluster_changes = [[] for _ in range(3)]
    for i, trend in enumerate(trends):
        cluster_changes[labels[i]].append(trend)

    # Select cluster with largest negative percentage change
    trending_cluster = max(cluster_changes, key=lambda c: -sum(t['percentage_change'] for t in c) if c else 0)
    trending_products = [t['product'] for t in trending_cluster if t['percentage_change'] < threshold]
    
    return trending_products[:5]