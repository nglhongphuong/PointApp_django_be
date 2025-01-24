from rest_framework import permissions
from rest_framework.permissions import BasePermission

class IsInGroup(BasePermission):
    message = 'You do not have permission to perform this action'

    def __init__(self, allowed_groups):
        self.allowed_groups = allowed_groups

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        user_groups = request.user.groups.values_list('name', flat=True)
        return any(group in user_groups for group in self.allowed_groups)


class IsInRole(BasePermission):
    message = 'You do not have permission to perform this action.'

    def __init__(self, allowed_roles):
        self.allowed_roles = allowed_roles

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # Kiểm tra role của user
        return request.user.role in self.allowed_roles

class ReadOnlyPermission(BasePermission):
    def has_permission(self, request, view):
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return request.user and request.user.is_staff
        if request.method == 'GET':
            return True
        return False


def classify_points(total_points):
    if total_points is None:
        return "Kém"
    if total_points >= 90:
        return "Xuất sắc"
    elif total_points >= 80:
        return "Tốt"
    elif total_points >= 65:
        return "Khá"
    elif total_points >= 50:
        return "Trung bình"
    elif total_points >= 35:
        return "Yếu"
    else:
        return "Kém"
