import csv
from io import StringIO
from celery import chain
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import Product, StockHistory
from .serializers import ShopifyWebhookSerializer

@shared_task
def import_product_data(csv_content):
    """
    Task 1: Import mock product data from CSV content.
    Returns list of product data dictionaries.
    """
    product_data = []
    csv_file = StringIO(csv_content)
    reader = csv.DictReader(csv_file)
    
    for row in reader:
        if 'sku' in row and 'inventory_quantity' in row:
            product_data.append({
                'sku': row['sku'],
                'inventory_quantity': int(row['inventory_quantity'])
            })
    return product_data

@shared_task
def validate_and_update_inventory(product_data):
    """
    Task 2: Validate imported data and update inventory quantities.
    Returns list of update results.
    """
    results = []
    for data in product_data:
        serializer = ShopifyWebhookSerializer(data=data)
        if serializer.is_valid():
            sku = serializer.validated_data['sku']
            inventory_quantity = serializer.validated_data['inventory_quantity']
            try:
                product = Product.objects.get(sku=sku)
                old_quantity = product.quantity
                StockHistory.objects.create(product=product, quantity=inventory_quantity)
                product.quantity = inventory_quantity
                product.save()
                results.append({
                    'sku': sku,
                    'status': 'success',
                    'old_quantity': old_quantity,
                    'new_quantity': inventory_quantity
                })
            except Product.DoesNotExist:
                results.append({
                    'sku': sku,
                    'status': 'error',
                    'error': 'Product not found'
                })
        else:
            results.append({
                'sku': data.get('sku', 'unknown'),
                'status': 'error',
                'error': serializer.errors
            })
    return results

@shared_task
def generate_and_email_report(results):
    """
    Task 3: Generate a report and email the summary.
    """
    subject = 'Nightly Inventory Update Report'
    message = 'Inventory Update Summary:\n\n'
    for result in results:
        if result['status'] == 'success':
            message += f"SKU: {result['sku']}, Updated from {result['old_quantity']} to {result['new_quantity']}\n"
        else:
            message += f"SKU: {result['sku']}, Error: {result['error']}\n"
    
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.DEFAULT_FROM_EMAIL],  # Replace with admin email
        fail_silently=False,
    )
    return {'status': 'Report emailed successfully'}

@shared_task
def nightly_inventory_update(csv_content):
    """
    Chain the three tasks for nightly execution.
    """
    chain(
        import_product_data.s(csv_content),
        validate_and_update_inventory.s(),
        generate_and_email_report.s()
    )()