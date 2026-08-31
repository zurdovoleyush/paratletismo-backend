from rest_framework import permissions
from .models import RoleChoices


class IsSuperAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == RoleChoices.SUPERADMIN


class IsOfficial(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == RoleChoices.OFFICIAL


class IsTournamentAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == RoleChoices.ADMIN


class IsInstitution(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == RoleChoices.INSTITUTION


class IsCoach(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == RoleChoices.COACH


class IsAthlete(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == RoleChoices.ATHLETE


class IsHeadJudge(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == RoleChoices.HEAD_JUDGE


class IsJudge(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == RoleChoices.JUDGE


class IsJudgeOrHeadJudge(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in [RoleChoices.JUDGE, RoleChoices.HEAD_JUDGE]


class IsAdminOrSuperAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in [RoleChoices.ADMIN, RoleChoices.SUPERADMIN]


class CanOrganizeTournament(permissions.BasePermission):
    """Permite crear torneos a usuarios habilitados sin depender de instituciones (que ahora son opcionales)."""
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.role in (RoleChoices.SUPERADMIN, RoleChoices.ADMIN, RoleChoices.INSTITUTION, RoleChoices.COACH):
            return True
        return user.is_superuser
