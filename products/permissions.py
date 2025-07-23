# products/permissions.py
from rest_framework import permissions

class IsInventoryManager(permissions.BasePermission):
    """
    Custom permission to allow access only to users in the 'Inventory Managers' group.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.groups.filter(name='Inventory Managers').exists()