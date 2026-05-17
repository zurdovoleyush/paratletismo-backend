import uuid
from django.db import models


class Discipline(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'config_disciplines'
        verbose_name_plural = 'Disciplinas'
        ordering = ['name']

    def __str__(self):
        return self.name


class Sex(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=10, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'config_sexes'
        ordering = ['name']

    def __str__(self):
        return self.name


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    min_age = models.IntegerField(null=True, blank=True, help_text='Edad minima')
    max_age = models.IntegerField(null=True, blank=True, help_text='Edad maxima')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'config_categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class FunctionalClassification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    discipline = models.ForeignKey(Discipline, on_delete=models.CASCADE, related_name='classifications')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'config_functional_classifications'
        unique_together = ['code', 'discipline']
        ordering = ['discipline', 'code']

    def __str__(self):
        return f'{self.code} - {self.name}'


class EventType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    discipline = models.ForeignKey(Discipline, on_delete=models.CASCADE, related_name='event_types')
    is_time_based = models.BooleanField(default=True, help_text='Si el resultado se mide en tiempo')
    is_distance_based = models.BooleanField(default=False, help_text='Si el resultado se mide en distancia')
    is_points_based = models.BooleanField(default=False, help_text='Si el resultado se mide en puntos')
    unit = models.CharField(max_length=20, default='segundos', help_text='Unidad de medida')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'config_event_types'
        ordering = ['discipline', 'name']

    def __str__(self):
        return f'{self.name} ({self.discipline})'
