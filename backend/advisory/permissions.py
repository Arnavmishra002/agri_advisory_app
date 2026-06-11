from rest_framework import permissions

class IsFarmer(permissions.BasePermission):
    """
    Custom permission to only allow farmers to access certain objects.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and hasattr(request.user, 'role') and request.user.role == 'farmer'

class IsAdmin(permissions.BasePermission):
    """
    Custom permission to only allow admins to access certain objects.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and hasattr(request.user, 'role') and request.user.role == 'admin'

class IsOfficer(permissions.BasePermission):
    """
    Custom permission to only allow officers to access certain objects.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and hasattr(request.user, 'role') and request.user.role == 'officer'

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to allow only owners of an object to edit or delete it.
    Read permissions are allowed to any authenticated user.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request, so we'll always allow GET, HEAD, or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the snippet.
        return obj.user == request.user
