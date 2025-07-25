from django.urls import path
from .views import ProductListCreateView, ProductDetailView, ShopifyInventoryWebhookView

app_name = 'products'

urlpatterns = [
    path('products/', ProductListCreateView.as_view(), name='product-list-create'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
    path('webhooks/shopify/inventory/', ShopifyInventoryWebhookView.as_view(), name='shopify-inventory-webhook'),
]
    
# SHOPIFY_WEBHOOK_SECRET=your-shopify-webhook-secret