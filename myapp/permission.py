from rest_framework.permissions import BasePermission

class IsAdminOrDenied(BasePermission):
    def has_permission(self, request, view):
        # Check if the user is authenticated and is an admin
        if request.user and request.user.is_staff:
            return True  # Allow access if the user is an admin
        return False  # Deny access if the user is not an admin
