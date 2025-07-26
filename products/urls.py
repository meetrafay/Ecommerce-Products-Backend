from django.urls import path
from .views import ProductDiscountView, ProductInsightsView, ProductListCreateView, ProductDetailView, ProductSearchView, ShopifyInventoryWebhookView

app_name = 'products'

urlpatterns = [
    path('products/', ProductListCreateView.as_view(), name='product-list-create'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
    path('products/<int:pk>/discount/', ProductDiscountView.as_view(), name='product-discount'),
    
    path('webhooks/shopify/inventory/', ShopifyInventoryWebhookView.as_view(), name='shopify-inventory-webhook'),
    
    path('products/search/', ProductSearchView.as_view(), name='product-search'),
    path('products/insights/', ProductInsightsView.as_view(), name='product-insights'),

]
    