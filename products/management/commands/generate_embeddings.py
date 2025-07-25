# products/management/commands/generate_embeddings.py
from django.core.management.base import BaseCommand
from django.core.cache import cache
from sentence_transformers import SentenceTransformer
from products.models import Product
import numpy as np

class Command(BaseCommand):
    help = 'Generate and cache embeddings for product names'

    def handle(self, *args, **options):
        model = SentenceTransformer('all-MiniLM-L6-v2')
        products = Product.objects.all()
        for product in products:
            # Generate embedding
            embedding = model.encode(product.name)
            # Store in database
            product.set_embedding(embedding)
            product.save()
            # Cache embedding
            cache_key = f"product_embedding_{product.sku}"
            cache.set(cache_key, embedding.tobytes(), timeout=None)  # No expiration
            self.stdout.write(self.style.SUCCESS(f"Generated embedding for {product.name} ({product.sku})"))