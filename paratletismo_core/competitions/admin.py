from django.contrib import admin
from .models import Registration, AthleteEvent, JudgeAssignment, Result, FinalResult


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ('athlete', 'tournament', 'institution', 'status', 'payment_status', 'registered_at')
    list_filter = ('status', 'payment_status', 'tournament')
    search_fields = ('athlete__user__email', 'tournament__name')


@admin.register(AthleteEvent)
class AthleteEventAdmin(admin.ModelAdmin):
    list_display = ('registration', 'tournament_event', 'bib_number', 'lane')
    list_filter = ('tournament_event',)


@admin.register(JudgeAssignment)
class JudgeAssignmentAdmin(admin.ModelAdmin):
    list_display = ('judge', 'tournament_event', 'is_head', 'assigned_at')
    list_filter = ('is_head', 'tournament_event')


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ('athlete_event', 'attempt_number', 'value', 'mark', 'is_valid', 'recorded_at')
    list_filter = ('is_valid',)


@admin.register(FinalResult)
class FinalResultAdmin(admin.ModelAdmin):
    list_display = ('athlete', 'tournament_event', 'rank', 'best_mark', 'is_dnf', 'is_dns', 'is_dq')
    list_filter = ('tournament_event', 'is_dnf', 'is_dns', 'is_dq')
    search_fields = ('athlete__user__first_name', 'athlete__user__last_name')
