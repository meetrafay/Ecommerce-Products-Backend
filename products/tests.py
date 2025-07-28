from functools import cache
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch
import numpy as np
from products.models import Product, StockHistory
from products.serializers import ProductSerializer
from authentication.models import Profile
from django.contrib.auth.models import User, Group
from products.tasks import nightly_inventory_update, update_trending_products
import base64
import hmac
import hashlib
from decouple import config

class ProductAPITestCase(APITestCase):
    def setUp(self):
        """Set up test data and authentication."""
        # Create a user and profile
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.profile = Profile.objects.create(user=self.user)
        self.client.force_authenticate(user=self.user)

        # Create Inventory Managers group and add user
        # self.group, _ = Group.objects.get_or_create(name='Inventory Managers')
        # self.user.groups.add(self.group)

        # Create test products
        self.product1 = Product.objects.create(
            name="Blue Wireless Mouse",
            sku="SP001",
            price=29.99,
            quantity=5,
            i_profile=self.profile,
            discount_percentage=10.00
        )
        self.product2 = Product.objects.create(
            name="Red Gaming Keyboard",
            sku="SP002",
            price=59.99,
            quantity=30,
            i_profile=self.profile
        )

        # Create stock history
        StockHistory.objects.create(
            product=self.product1,
            quantity=50,
            timestamp=timezone.now() - timedelta(days=5)
        )
        StockHistory.objects.create(
            product=self.product1,
            quantity=5,
            timestamp=timezone.now()
        )
        StockHistory.objects.create(
            product=self.product2,
            quantity=35,
            timestamp=timezone.now() - timedelta(days=5)
        )
        StockHistory.objects.create(
            product=self.product2,
            quantity=30,
            timestamp=timezone.now()
        )

    def test_product_list_create(self):
        """Test listing and creating products."""
        url = reverse('products:product-list-create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['sku'], 'SP001')

        # Test filtering
        response = self.client.get(url, {'price_min': 50})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['sku'], 'SP002')

        # Test POST /api/products/
        data = {
            'name': 'USB-C Cable',
            'sku': 'SP003',
            'price': 9.99,
            'quantity': 100,
            'discount_percentage': 5.00
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Product.objects.count(), 3)
        self.assertEqual(response.data['sku'], 'SP003')

    def test_product_detail(self):
        """Test retrieving, updating, and deleting a product."""
        url = reverse('products:product-detail', kwargs={'pk': self.product1.pk})

        # Test GET /api/products/<id>/
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['sku'], 'SP001')
        self.assertEqual(float(response.data['discounted_price']), 26.99)

        # Test PUT /api/products/<id>/
        data = {
            'name': 'Updated Mouse',
            'sku': 'SP001',
            'price': 34.99,
            'quantity': 10,
            'discount_percentage': 0.00
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.name, 'Updated Mouse')
        self.assertEqual(float(self.product1.price), 34.99)

        # Test DELETE /api/products/<id>/
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Product.objects.count(), 1)

    @patch('products.utils.compute_similarity')
    def test_product_search(self, mock_compute_similarity):
        """Test semantic search with mocked compute_similarity."""
        mock_compute_similarity.return_value = [self.product1]
        url = reverse('products:product-search')
        response = self.client.get(url, {'q': 'mouse'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['sku'], 'SP001')

        # Test empty query
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_product_insights(self):
        """Test insights endpoint with statistics and trending products."""
        url = reverse('products:product-insights')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('statistics', response.data)
        self.assertIn('trending_products', response.data)
        self.assertEqual(response.data['statistics']['total_products'], 2)
        self.assertEqual(response.data['statistics']['low_stock_products'], 1)
        self.assertAlmostEqual(response.data['statistics']['low_stock_percentage'], 50.0)
        self.assertEqual(len(response.data['trending_products']), 1)
        self.assertEqual(response.data['trending_products'][0]['sku'], 'SP001')

    def test_product_discount(self):
        """Test adding/updating product discount."""
        url = reverse('products:product-discount', kwargs={'pk': self.product1.pk})
        data = {'discount_percentage': 20.00}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product1.refresh_from_db()
        self.assertEqual(float(self.product1.discount_percentage), 20.00)
        self.assertEqual(float(response.data['discounted_price']), 23.99)

        # Test invalid discount
        data = {'discount_percentage': 150.00}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('discount_percentage', response.data)

    # def test_shopify_webhook(self):
    #     """Test Shopify inventory update webhook."""
    #     url = reverse('products:shopify-inventory-webhook')
    #     payload = {
    #         'sku': 'SP001',
    #         'inventory_quantity': 50
    #     }

    #     # Generate HMAC
    #     secret = config('SHOPIFY_WEBHOOK_SECRET', default='test_secret')
    #     import json
    #     data = json.dumps(payload).encode('utf-8')
    #     digest = hmac.new(secret.encode('utf-8'), data, hashlib.sha256).digest()
    #     hmac_header = base64.b64encode(digest).decode('utf-8')

    #     # Test valid webhook
    #     with patch('products.utils.verify_shopify_webhook', return_value=True):
    #         response = self.client.post(
    #             url,
    #             data=payload,
    #             format='json',
    #             HTTP_X_SHOPIFY_HMAC_SHA256=hmac_header
    #         )
    #         self.assertEqual(response.status_code, status.HTTP_200_OK)
    #         self.product1.refresh_from_db()
    #         self.assertEqual(self.product1.quantity, 50)
    #         self.assertEqual(StockHistory.objects.filter(product=self.product1).count(), 3)

        # Test invalid HMAC
        # with patch('products.utils.verify_shopify_webhook', return_value=False):
        #     response = self.client.post(
        #         url,
        #         data=payload,
        #         format='json',
        #         HTTP_X_SHOPIFY_HMAC_SHA256='invalid_hmac'
        #     )
        #     self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

class CeleryTaskTestCase(TestCase):
    def setUp(self):
        """Set up test data for Celery tasks."""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.profile = Profile.objects.create(user=self.user)
        self.product1 = Product.objects.create(
            name="Blue Wireless Mouse",
            sku="SP001",
            price=29.99,
            quantity=5,
            i_profile=self.profile
        )
        self.product2 = Product.objects.create(
            name="Red Gaming Keyboard",
            sku="SP002",
            price=59.99,
            quantity=30,
            i_profile=self.profile
        )
        StockHistory.objects.create(
            product=self.product1,
            quantity=50,
            timestamp=timezone.now() - timedelta(days=5)
        )
        StockHistory.objects.create(
            product=self.product1,
            quantity=5,
            timestamp=timezone.now()
        )

    @patch('products.tasks.send_mail')
    def test_nightly_inventory_update(self, mock_send_mail):
        """Test nightly inventory update Celery task."""
        csv_content = "sku,inventory_quantity\nSP001,100\nSP002,50\n"
        nightly_inventory_update(csv_content)
        self.product1.refresh_from_db()
        self.product2.refresh_from_db()
        self.assertEqual(self.product1.quantity, 100)
        self.assertEqual(self.product2.quantity, 50)
        self.assertEqual(StockHistory.objects.filter(product=self.product1).count(), 3)
        self.assertTrue(mock_send_mail.called)

    @patch('products.utils.compute_trending_products')
    def test_update_trending_products(self, mock_compute_trending_products):
        """Test trending products update Celery task."""
        mock_compute_trending_products.return_value = [self.product1]
        update_trending_products()
        trending_products = cache.get('trending_products')
        self.assertIsNotNone(trending_products)
        self.assertEqual(len(trending_products), 1)
        self.assertEqual(trending_products[0]['sku'], 'SP001')