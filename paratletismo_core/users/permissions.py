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
    """Solo permite crear torneos si el usuario tiene permiso activo."""
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.role in (RoleChoices.SUPERADMIN, RoleChoices.ADMIN):
            return True
        if user.role == RoleChoices.COACH:
            return True
        if user.role == RoleChoices.INSTITUTION:
            from paratletismo_core.tournaments.models import InstitutionUser
            iu = InstitutionUser.objects.filter(user=user).first()
            return iu is not None and iu.institution.can_organize
        return user.is_superuser
