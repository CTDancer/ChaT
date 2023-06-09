from django.contrib.auth import get_user_model
from rest_framework import permissions
from rest_framework.permissions import SAFE_METHODS

# PATCH 方法不检查权限！！！
MODIFY_METHODS = ('PUT', 'DELETE')
CORS_METHODS = ('OPTIONS',)


class OnlyAdminCanModify(permissions.BasePermission):
    """
    适用于主题帖
    """

    def has_permission(self, request, view):
        if request.method in MODIFY_METHODS:
            return request.user.is_admin or request.user.is_superuser 
        else:
            return True


class AdminOnly(permissions.BasePermission):

    def has_permission(self, request, view):
        return request.user.is_admin

class SuperuserOnly(permissions.BasePermission):

    def has_permission(self, request, view):
        return request.user.is_admin or request.user.is_superuser

class NotSilentOrAdminCanPost(permissions.BasePermission):
    """
    在给定分区内是否具有发帖权限，传入一个 division_id
    """

    def has_object_permission(self, request, view, division_id):
        if request.method == 'POST':
            return not request.user.is_silenced(division_id) or request.user.is_admin or request.user.is_superuser
        else:
            return True


class AdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        else:
            return request.user.is_admin or request.user.is_superuser


class AdminOrPostOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in ('POST', 'OPTIONS'):
            return True
        else:
            return request.user.is_admin or request.user.is_superuser


class OwenerOrAdminCanSee(permissions.BasePermission):
    def has_object_permission(self, request, view, instance):
        if request.method == 'GET':
            owner = instance if type(instance) == get_user_model() else instance.user
            return owner == request.user or request.user.is_admin or request.user.is_superuser
        else:
            return True


class OwnerOrAdminCanModify(permissions.BasePermission):
    """
    适用于回复帖或用户资料
    """

    def has_object_permission(self, request, view, instance):
        if request.method in MODIFY_METHODS:
            owner = instance if type(instance) == get_user_model() else instance.user
            return owner == request.user or request.user.is_admin or request.user.is_superuser
        else:
            return True


class IsAuthenticatedEx(permissions.BasePermission):
    """
    Allows access only to authenticated users.
    But also allows CORS preflight, i.e. OPTIONS.
    """

    def has_permission(self, request, view):
        if request.method in CORS_METHODS:
            return True
        else:
            return bool(request.user and request.user.is_authenticated)
