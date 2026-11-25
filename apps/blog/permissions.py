from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request


class IsAuthorOrStaffForDelete(BasePermission):
    """Reading: for everyone. Patch: author. Delete: auhtor or staff"""

    def has_object_permission(self, request: Request, view, obj) -> bool:
        if request.method in SAFE_METHODS:
            return True
        is_author = obj.author_id == request.user.id
        if request.method == "DELETE":
            return is_author or request.user.is_staff
        return is_author