import uuid
from django.db import models
from django.conf import settings
from paratletismo_core.config.models import Discipline, Sex, Category


class Institution(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=300, blank=True)
    city = models.CharField(max_length=100, blank=True)
    province = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True, null=True)
    logo = models.ImageField(upload_to='institutions/', blank=True, null=True)
    founded_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tournaments_institutions'
        ordering = ['name']

    def __str__(self):
        return self.name


class InstitutionUser(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='users')
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='institution_profile')
    position = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tournaments_institution_users'
        verbose_name = 'Usuario Institucion'

    def __str__(self):
        return f'{self.user} - {self.institution}'


class Coach(models.Model):
    DOCUMENT_TYPES = [
        ('dni', 'DNI'),
        ('passport', 'Pasaporte'),
        ('le', 'Libreta de Enrolamiento'),
        ('lc', 'Libreta Civica'),
        ('other', 'Otro'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='coach_profile')
    institution = models.ForeignKey(Institution, on_delete=models.SET_NULL, null=True, blank=True, related_name='coaches')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES, default='dni')
    document_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    specialties = models.TextField(blank=True, help_text='Especialidades del entrenador')
    license_number = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tournaments_coaches'

    def __str__(self):
        return str(self.user)


class Athlete(models.Model):
    DOCUMENT_TYPES = [
        ('dni', 'DNI'),
        ('passport', 'Pasaporte'),
        ('le', 'Libreta de Enrolamiento'),
        ('lc', 'Libreta Civica'),
        ('other', 'Otro'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='athlete_profile')
    institution = models.ForeignKey(Institution, on_delete=models.SET_NULL, null=True, blank=True, related_name='athletes')
    coach = models.ForeignKey(Coach, on_delete=models.SET_NULL, null=True, blank=True, related_name='athletes')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES, default='dni')
    document_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    date_of_birth = models.DateField()
    sex = models.ForeignKey('config.Sex', on_delete=models.SET_NULL, null=True, blank=True)
    functional_classification = models.ForeignKey('config.FunctionalClassification', on_delete=models.SET_NULL, null=True, blank=True, related_name='athletes')
    classification_status = models.CharField(
        max_length=20,
        choices=[('provisional', 'Provisoria'), ('confirmed', 'Confirmada')],
        default='provisional'
    )
    classification_notes = models.TextField(blank=True)
    classified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='classifications_made',
        help_text='Oficial que confirmo la clasificacion'
    )
    classification_date = models.DateTimeField(null=True, blank=True)
    emergency_contact = models.CharField(max_length=200, blank=True)
    emergency_phone = models.CharField(max_length=20, blank=True)
    medical_info = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tournaments_athletes'

    def __str__(self):
        return str(self.user)

    @property
    def age(self):
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))


class Tournament(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Borrador'),
        ('registration_open', 'Inscripcion Abierta'),
        ('registration_closed', 'Inscripcion Cerrada'),
        ('in_progress', 'En Progreso'),
        ('completed', 'Completado'),
        ('cancelled', 'Cancelado'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    organizer = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='organized_tournaments')
    admin_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='administered_tournaments')
    venue = models.CharField(max_length=300)
    address = models.CharField(max_length=300)
    city = models.CharField(max_length=100)
    province = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    registration_opens = models.DateTimeField()
    registration_closes = models.DateTimeField()
    tournament_start = models.DateTimeField()
    tournament_end = models.DateTimeField()
    registration_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='Costo de inscripcion por atleta')
    max_participants = models.IntegerField(null=True, blank=True)
    disciplines = models.ManyToManyField(Discipline, related_name='tournaments')
    sexes = models.ManyToManyField(Sex, related_name='tournaments')
    categories = models.ManyToManyField(Category, related_name='tournaments')
    logo = models.ImageField(upload_to='tournaments/', blank=True, null=True)
    rules = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tournaments_tournaments'
        ordering = ['-tournament_start']

    def __str__(self):
        return self.name


class TournamentEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='events')
    name = models.CharField(max_length=200)
    event_type = models.ForeignKey('config.EventType', on_delete=models.SET_NULL, null=True, blank=True)
    discipline = models.ForeignKey(Discipline, on_delete=models.SET_NULL, null=True, blank=True)
    sex = models.ForeignKey(Sex, on_delete=models.PROTECT)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    functional_classification = models.ForeignKey('config.FunctionalClassification', on_delete=models.SET_NULL, null=True, blank=True)
    scheduled_date = models.DateTimeField()
    scheduled_time = models.TimeField(null=True, blank=True)
    venue_detail = models.CharField(max_length=200, blank=True, help_text='Pista, sector, etc.')
    status = models.CharField(
        max_length=20,
        choices=[('scheduled', 'Programada'), ('in_progress', 'En Curso'), ('completed', 'Completada'), ('cancelled', 'Cancelada')],
        default='scheduled'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tournaments_tournament_events'
        ordering = ['scheduled_date', 'name']

    def __str__(self):
        return f'{self.name} - {self.tournament}'
