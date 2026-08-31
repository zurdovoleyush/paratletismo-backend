import uuid
from django.db import models
from django.conf import settings
from paratletismo_core.config.models import Discipline, Sex, Category, FunctionalClassification


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
    is_active = models.BooleanField(default=True, help_text='Institución activa (visible en listados)')
    can_organize = models.BooleanField(default=False, help_text='Puede crear torneos (previo pago)')
    organized_until = models.DateField(null=True, blank=True, help_text='Vencimiento del permiso para organizar torneos')
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


class OrganizationPayment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2, help_text='Monto abonado')
    payment_date = models.DateTimeField(auto_now_add=True)
    valid_from = models.DateField(help_text='Inicio de vigencia')
    valid_until = models.DateField(help_text='Fin de vigencia')
    paid_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments_registered', help_text='Admin que registró el pago')
    notes = models.TextField(blank=True, help_text='Observaciones')

    class Meta:
        db_table = 'tournaments_organization_payments'
        ordering = ['-payment_date']

    def __str__(self):
        return f'{self.institution.name} - ${self.amount} ({self.valid_from} a {self.valid_until})'


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
    date_of_birth = models.DateField(null=True, blank=True)
    sex = models.ForeignKey('config.Sex', on_delete=models.SET_NULL, null=True, blank=True)
    functional_classification = models.ForeignKey('config.FunctionalClassification', on_delete=models.SET_NULL, null=True, blank=True, related_name='athletes')
    track_classification = models.ForeignKey('config.FunctionalClassification', on_delete=models.SET_NULL, null=True, blank=True, related_name='track_athletes', help_text='Clasificacion funcional de pista (T)')
    field_classification = models.ForeignKey('config.FunctionalClassification', on_delete=models.SET_NULL, null=True, blank=True, related_name='field_athletes', help_text='Clasificacion funcional de campo (F)')
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
    phone = models.CharField(max_length=20, blank=True, help_text='Telefono del atleta')
    emergency_contact = models.CharField(max_length=200, blank=True)
    emergency_phone = models.CharField(max_length=20, blank=True)
    medical_info = models.TextField(blank=True)
    address_country = models.CharField(max_length=100, blank=True, default='Argentina', help_text='Pais de residencia')
    address_province = models.CharField(max_length=100, blank=True)
    address_city = models.CharField(max_length=100, blank=True)
    address_street = models.CharField(max_length=300, blank=True, help_text='Direccion (calle y numero)')
    guardian_name = models.CharField(max_length=300, blank=True, help_text='Nombre completo del adulto responsable')
    guardian_document_type = models.CharField(max_length=20, blank=True, choices=DOCUMENT_TYPES)
    guardian_document_number = models.CharField(max_length=20, blank=True)
    guardian_phone = models.CharField(max_length=20, blank=True)
    guardian_email = models.EmailField(blank=True)
    guardian_address_country = models.CharField(max_length=100, blank=True, default='Argentina')
    guardian_address_province = models.CharField(max_length=100, blank=True)
    guardian_address_city = models.CharField(max_length=100, blank=True)
    guardian_address_street = models.CharField(max_length=300, blank=True)
    profile_image = models.ImageField(upload_to='athletes/profiles/', blank=True, null=True, help_text='Foto de perfil')
    cud_file = models.FileField(upload_to='athletes/cud/', blank=True, null=True, help_text='Certificado Unico de Discapacidad (CUD)')
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

    def category_age(self, reference_year=None):
        from datetime import date
        if not self.date_of_birth:
            return None
        year = reference_year or date.today().year
        return year - self.date_of_birth.year

    @property
    def is_minor(self):
        return self.age <= 17


class Tournament(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Borrador'),
        ('registration_open', 'Inscripcion Abierta'),
        ('registration_closed', 'Inscripcion Cerrada'),
        ('in_progress', 'En Progreso'),
        ('completed', 'Completado'),
        ('cancelled', 'Cancelado'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pendiente de pago'),
        ('paid', 'Habilitado'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    organizer = models.ForeignKey(Institution, on_delete=models.SET_NULL, null=True, blank=True, related_name='organized_tournaments', help_text='Opcional: institucion que organiza (no condiciona la creacion del torneo)')
    admin_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='administered_tournaments')
    venue = models.CharField(max_length=300)
    address = models.CharField(max_length=300)
    city = models.CharField(max_length=100)
    province = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending',
        help_text='Habilitacion del torneo tras el pago del servicio'
    )
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text='Monto abonado por el servicio del torneo')
    payment_date = models.DateTimeField(null=True, blank=True, help_text='Fecha en que se registro el pago')
    payment_notes = models.TextField(blank=True, help_text='Observaciones del pago')
    paid_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='tournament_payments_registered', help_text='Admin que habilito el torneo')
    is_active = models.BooleanField(default=True, help_text='Torneo visible en el perfil del organizador y habilitado para el publico')
    registration_opens = models.DateTimeField()
    registration_closes = models.DateTimeField()
    tournament_start = models.DateTimeField()
    tournament_end = models.DateTimeField()
    registration_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='Costo de inscripcion por atleta')
    max_participants = models.IntegerField(null=True, blank=True)
    disciplines = models.ManyToManyField(Discipline, related_name='tournaments')
    sexes = models.ManyToManyField(Sex, related_name='tournaments')
    categories = models.ManyToManyField(Category, related_name='tournaments')
    functional_classifications = models.ManyToManyField(FunctionalClassification, blank=True, related_name='tournaments')
    head_judge = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='tournaments_as_head_judge', help_text='Juez principal del torneo')
    max_events_per_athlete = models.IntegerField(default=0, help_text='0 = sin limite')
    logo = models.ImageField(upload_to='tournaments/', blank=True, null=True)
    rules = models.TextField(blank=True)
    use_bibs = models.BooleanField(
        default=True,
        help_text='El torneo utiliza pecheras numeradas (dorsales)'
    )
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
    sex = models.ForeignKey(Sex, on_delete=models.PROTECT, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, null=True, blank=True)
    functional_classification = models.ForeignKey('config.FunctionalClassification', on_delete=models.SET_NULL, null=True, blank=True)
    sexes = models.ManyToManyField('config.Sex', blank=True, related_name='tournament_events')
    categories = models.ManyToManyField('config.Category', blank=True, related_name='tournament_events')
    functional_classifications = models.ManyToManyField('config.FunctionalClassification', blank=True, related_name='tournament_events')
    scheduled_date = models.DateTimeField(null=True, blank=True)
    scheduled_time = models.TimeField(null=True, blank=True, help_text='Hora de la prueba')
    call_time = models.TimeField(null=True, blank=True, help_text='Hora de camara de llamada')
    venue_detail = models.CharField(max_length=200, blank=True, help_text='Pista, sector, etc.')
    is_final = models.BooleanField(default=False, help_text='Prueba oficial del programa (con inscriptos) tras cerrar la inscripcion')
    status = models.CharField(
        max_length=20,
        choices=[('scheduled', 'Programada'), ('in_progress', 'En Curso'), ('completed', 'Completada'), ('cancelled', 'Cancelada')],
        default='scheduled'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tournaments_tournament_events'
        ordering = ['scheduled_date', 'name']

    def uses_track_classification(self):
        fcs = list(self.functional_classifications.all())
        if not fcs and self.functional_classification:
            fcs = [self.functional_classification]
        if fcs:
            return fcs[0].code.upper().startswith('T')
        return bool(self.event_type and self.event_type.is_time_based)

    def __str__(self):
        return f'{self.name} - {self.tournament}'
