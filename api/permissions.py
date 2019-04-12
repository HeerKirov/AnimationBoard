from rest_framework import permissions
from . import models as app_models
from django.utils import timezone


class BasePermission(permissions.BasePermission):
    LOGIN_REFRESH_INTERVAL = 60 * 30     # seconds

    def has_permission(self, request, view):
        if request.user.is_authenticated:
            profile = request.user.profile
            now = timezone.now()
            if profile.last_login_time is None or \
                    (now - profile.last_login_time).seconds >= self.LOGIN_REFRESH_INTERVAL:
                profile.last_login_time = now
                profile.last_login_ip = request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR')
                profile.save()


class IsLogin(BasePermission):
    def has_permission(self, request, view):
        super().has_permission(request, view)
        user = request.user
        return user is not None and user.is_authenticated


# 对于私有api的权限。仅持有者可rw。
class SelfOnly(BasePermission):
    def has_permission(self, request, view):
        super().has_permission(request, view)
        return request.user is not None and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.user is None or request.user.is_authenticated is False:
            return False
        profile = request.user.profile
        if obj is None:
            return False
        elif isinstance(obj, app_models.Profile):
            return obj.username == profile.username
        elif isinstance(obj, app_models.User):
            return obj.username == profile.username
        elif hasattr(obj, 'owner'):
            return getattr(obj, 'owner').username == profile.username
        else:
            return False


class IsStaffOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        super().has_permission(request, view)
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        if user is not None:
            return user.is_authenticated and user.is_staff


class IsStaff(BasePermission):
    def has_permission(self, request, view):
        super().has_permission(request, view)
        user = request.user
        return user is not None and user.is_authenticated and user.is_staff


class Above(BasePermission):
    def has_permission(self, request, view):
        super().has_permission(request, view)
        user = request.user
        return user is not None and user.is_authenticated and user.is_staff

    def has_object_permission(self, request, view, obj):
        user = request.user
        is_staff = user is not None and user.is_authenticated and user.is_staff
        is_superuser = is_staff and user.is_superuser
        level = 3 if is_superuser else 2 if is_staff else 1

        obj_user = obj.user
        obj_is_staff = obj_user is not None and obj_user.is_authenticated and obj_user.is_staff
        obj_is_superuser = obj_is_staff and obj_user.is_superuser
        obj_level = 3 if obj_is_superuser else 2 if obj_is_staff else 1

        return is_staff and level > obj_level


class IsSuperuser(BasePermission):
    def has_permission(self, request, view):
        super().has_permission(request, view)
        user = request.user
        return user is not None and user.is_authenticated and user.is_superuser
