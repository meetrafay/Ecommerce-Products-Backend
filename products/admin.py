from django.contrib import admin
from django.contrib.admin import DateFieldListFilter
from django.db.models import F  # Import F for database-level operations
from .models import Product, StockHistory

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Admin interface for Product model with advanced filtering and bulk price update actions.
    """
    list_display = ('name', 'sku', 'price', 'quantity', 'last_updated', 'i_profile', 'embedding')
    list_filter = (
        'sku',
        'name',
        ('last_updated', DateFieldListFilter),  # Advanced date-based filtering
    )
    search_fields = ('name', 'sku')  # Search by name and SKU
    list_per_page = 25  # Pagination for better usability
    ordering = ('-last_updated',)  # Default sort by last_updated (descending)
    date_hierarchy = 'last_updated'  # Drill-down navigation by date

    actions = ['increase_price_10_percent', 'decrease_price_10_percent']

    def increase_price_10_percent(self, request, queryset):
        """
        Bulk action to increase product prices by 10%.
        """
        updated = queryset.update(price=F('price') * 1.1)
        self.message_user(request, f"{updated} products' prices increased by 10%%.")  # Escape % with %%

    increase_price_10_percent.short_description = "Increase selected products' prices by 10%%"  # Escape % with %%

    def decrease_price_10_percent(self, request, queryset):
        """
        Bulk action to decrease product prices by 10%.
        """
        updated = queryset.update(price=F('price') * 0.9)
        self.message_user(request, f"{updated} products' prices decreased by 10%%.")  # Escape % with %%

    decrease_price_10_percent.short_description = "Decrease selected products' prices by 10%%"  # Escape % with %%
    
@admin.register(StockHistory)
class StockHistoryAdmin(admin.ModelAdmin):
    """
    Admin interface for StockHistory model.
    Displays stock changes with timestamps.
    """
    list_display = ('product', 'quantity', 'timestamp')

