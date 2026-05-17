from django.contrib import admin
from .models import Discipline, Sex, Category, FunctionalClassification, EventType


@admin.register(Discipline)
class DisciplineAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(Sex)
class SexAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active')
    search_fields = ('name', 'code')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'min_age', 'max_age', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(FunctionalClassification)
class FunctionalClassificationAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'discipline', 'is_active')
    list_filter = ('discipline', 'is_active')
    search_fields = ('code', 'name')


@admin.register(EventType)
class EventTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'discipline', 'is_time_based', 'is_distance_based', 'unit', 'is_active')
    list_filter = ('discipline', 'is_active')
    search_fields = ('name',)
