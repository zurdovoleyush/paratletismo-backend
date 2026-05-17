from django.contrib import admin
from .models import Institution, InstitutionUser, Coach, Athlete, Tournament, TournamentEvent


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'province', 'created_at')
    search_fields = ('name', 'city')


@admin.register(InstitutionUser)
class InstitutionUserAdmin(admin.ModelAdmin):
    list_display = ('user', 'institution', 'position')
    list_filter = ('institution',)


@admin.register(Coach)
class CoachAdmin(admin.ModelAdmin):
    list_display = ('user', 'institution', 'license_number')
    list_filter = ('institution',)
    search_fields = ('user__email', 'user__first_name', 'user__last_name')


@admin.register(Athlete)
class AthleteAdmin(admin.ModelAdmin):
    list_display = ('user', 'institution', 'coach', 'classification_status', 'date_of_birth')
    list_filter = ('classification_status', 'institution', 'sex')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ('name', 'organizer', 'status', 'tournament_start', 'tournament_end')
    list_filter = ('status', 'disciplines')
    search_fields = ('name', 'venue', 'city')


@admin.register(TournamentEvent)
class TournamentEventAdmin(admin.ModelAdmin):
    list_display = ('name', 'tournament', 'discipline', 'sex', 'category', 'scheduled_date', 'status')
    list_filter = ('status', 'discipline', 'sex', 'category')
    search_fields = ('name',)
