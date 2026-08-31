import uuid
from django.db import models
from django.conf import settings


class Registration(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('approved', 'Aprobada'),
        ('rejected', 'Rechazada'),
        ('withdrawn', 'Retirada'),
    ]

    PAYMENT_STATUS = [
        ('pending', 'Pendiente'),
        ('paid', 'Pagado'),
        ('exempt', 'Exento'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tournament = models.ForeignKey('tournaments.Tournament', on_delete=models.CASCADE, related_name='registrations')
    athlete = models.ForeignKey('tournaments.Athlete', on_delete=models.CASCADE, related_name='registrations')
    institution = models.ForeignKey('tournaments.Institution', on_delete=models.CASCADE, related_name='registrations')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    registered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='registrations_made')
    registered_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    medical_certificate = models.FileField(upload_to='registrations/medical/', blank=True, null=True, help_text='Certificado medico apto')
    payment_receipt = models.FileField(upload_to='registrations/payments/', blank=True, null=True, help_text='Comprobante de pago')
    rejection_reason = models.TextField(blank=True, help_text='Motivo del rechazo informado al atleta/institucion')

    class Meta:
        db_table = 'competitions_registrations'
        unique_together = ['tournament', 'athlete']
        ordering = ['-registered_at']

    def __str__(self):
        return f'{self.athlete} - {self.tournament}'


class AthleteEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='athlete_events')
    tournament_event = models.ForeignKey('tournaments.TournamentEvent', on_delete=models.CASCADE, related_name='athlete_events')
    bib_number = models.IntegerField(null=True, blank=True)
    lane = models.IntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pendiente'), ('confirmed', 'Confirmada'), ('withdrawn', 'Retirada'), ('dnf', 'DNF'), ('dq', 'Descalificado')],
        default='pending'
    )

    class Meta:
        db_table = 'competitions_athlete_events'
        unique_together = ['tournament_event', 'registration']
        ordering = ['tournament_event', 'bib_number']

    def __str__(self):
        return f'{self.registration.athlete} - {self.tournament_event}'


class JudgeAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tournament_event = models.ForeignKey('tournaments.TournamentEvent', on_delete=models.CASCADE, related_name='judge_assignments')
    judge = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='judge_assignments')
    is_head = models.BooleanField(default=False)
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='assignments_made')
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'competitions_judge_assignments'
        unique_together = ['tournament_event', 'judge']

    def __str__(self):
        return f'{self.judge} - {self.tournament_event}'


class Result(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    athlete_event = models.ForeignKey(AthleteEvent, on_delete=models.CASCADE, related_name='results')
    attempt_number = models.IntegerField()
    value = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, help_text='Resultado numerico')
    mark = models.CharField(max_length=100, blank=True, help_text='Marca textual (ej: 1:23.45)')
    is_valid = models.BooleanField(default=True)
    wind = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, help_text='Velocidad del viento')
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='results_recorded')
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'competitions_results'
        ordering = ['athlete_event', 'attempt_number']


class FinalResult(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tournament_event = models.ForeignKey('tournaments.TournamentEvent', on_delete=models.CASCADE, related_name='final_results')
    athlete = models.ForeignKey('tournaments.Athlete', on_delete=models.CASCADE)
    rank = models.IntegerField(null=True, blank=True)
    best_mark = models.CharField(max_length=100, blank=True)
    points = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    record_type = models.CharField(
        max_length=20,
        choices=[
            ('tournament', 'Record del Torneo'),
            ('national', 'Record Nacional'),
            ('american', 'Record Americano'),
            ('world', 'Record Mundial'),
        ],
        blank=True
    )
    is_dnf = models.BooleanField(default=False, help_text='Did Not Finish')
    is_dns = models.BooleanField(default=False, help_text='Did Not Start')
    is_dq = models.BooleanField(default=False, help_text='Disqualified')
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='results_verified')
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'competitions_final_results'
        unique_together = ['tournament_event', 'athlete']
        ordering = ['tournament_event', 'rank']

    def __str__(self):
        return f'{self.athlete} - {self.tournament_event} - Rank #{self.rank}'
