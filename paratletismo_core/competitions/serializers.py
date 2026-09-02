from rest_framework import serializers
from .models import Registration, AthleteEvent, JudgeAssignment, Result, FinalResult


class RegistrationSerializer(serializers.ModelSerializer):
    athlete_name = serializers.CharField(source='athlete.user.get_full_name', read_only=True)
    tournament_name = serializers.CharField(source='tournament.name', read_only=True)
    institution_name = serializers.CharField(source='institution.name', read_only=True)
    registered_by_name = serializers.CharField(source='registered_by.get_full_name', read_only=True)

    class Meta:
        model = Registration
        fields = [
            'id', 'tournament', 'tournament_name', 'athlete', 'athlete_name',
            'institution', 'institution_name', 'status', 'payment_status',
            'registered_by', 'registered_by_name', 'registered_at', 'notes',
            'medical_certificate', 'payment_receipt', 'rejection_reason',
        ]
        read_only_fields = ['id', 'registered_at']


class RegistrationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Registration
        fields = ['id', 'tournament', 'athlete', 'notes', 'medical_certificate', 'payment_receipt', 'status']
        read_only_fields = ['id', 'status']

    def validate(self, data):
        user = self.context['request'].user
        athlete = data['athlete']
        tournament = data['tournament']
        if not data.get('medical_certificate'):
            raise serializers.ValidationError({'medical_certificate': 'La ficha medica (certificado medico apto) es obligatoria'})
        if not data.get('payment_receipt'):
            raise serializers.ValidationError({'payment_receipt': 'El comprobante de pago es obligatorio'})
        if tournament.payment_status != 'paid':
            raise serializers.ValidationError({'tournament': 'El torneo aun no esta habilitado (pendiente de pago)'})
        if not tournament.is_active:
            raise serializers.ValidationError({'tournament': 'El torneo esta inactivo y no acepta inscripciones'})
        from paratletismo_core.tournaments.models import Coach, InstitutionUser
        if user.role == 'coach':
            try:
                coach = Coach.objects.get(user=user)
                if athlete.coach and athlete.coach.id != coach.id:
                    raise serializers.ValidationError({'athlete': 'Solo puedes inscribir atletas que tengas asignados como entrenador'})
                if not athlete.coach:
                    raise serializers.ValidationError({'athlete': 'Este atleta no tiene un entrenador asignado'})
            except Coach.DoesNotExist:
                raise serializers.ValidationError({'athlete': 'No tienes un perfil de entrenador'})
        elif user.role == 'institution':
            try:
                inst_user = InstitutionUser.objects.get(user=user)
                if athlete.institution and athlete.institution.id != inst_user.institution.id:
                    raise serializers.ValidationError({'athlete': 'Solo puedes inscribir atletas de tu institucion'})
                if not athlete.institution:
                    raise serializers.ValidationError({'athlete': 'Este atleta no pertenece a ninguna institucion'})
            except InstitutionUser.DoesNotExist:
                raise serializers.ValidationError({'athlete': 'No tienes una institucion asignada'})
        return data

    def create(self, validated_data):
        athlete = validated_data['athlete']
        validated_data['institution'] = athlete.institution
        validated_data['registered_by'] = self.context['request'].user
        return Registration.objects.create(**validated_data)


class AthleteEventRegistrationSerializer(serializers.Serializer):
    athlete = serializers.UUIDField()
    tournament_event = serializers.UUIDField()

    def validate(self, data):
        from paratletismo_core.tournaments.models import TournamentEvent, Athlete
        athlete = Athlete.objects.get(id=data['athlete'])
        event = TournamentEvent.objects.get(id=data['tournament_event'])

        event_sexes = list(event.sexes.all()) if event.sexes.exists() else ([event.sex] if event.sex else [])
        if athlete.sex and event_sexes and athlete.sex not in event_sexes:
            sex_names = ', '.join(s.name for s in event_sexes)
            raise serializers.ValidationError({'athlete': f'El sexo del atleta no corresponde a esta prueba (requerido: {sex_names})'})

        event_cats = list(event.categories.all()) if event.categories.exists() else ([event.category] if event.category else [])
        if event_cats:
            from datetime import date
            ref_year = event.tournament.tournament_start.year if event.tournament.tournament_start else date.today().year
            age = athlete.category_age(ref_year)
            age_ok = False
            for cat in event_cats:
                if cat.min_age and age < cat.min_age:
                    continue
                if cat.max_age and age > cat.max_age:
                    continue
                age_ok = True
                break
            if not age_ok:
                cat_names = ', '.join(c.name for c in event_cats)
                raise serializers.ValidationError({'athlete': f'La edad del atleta no corresponde a ninguna categoria de esta prueba ({cat_names})'})

        event_fcs = list(event.functional_classifications.all())
        if not event_fcs and event.functional_classification:
            event_fcs = [event.functional_classification]
        if event_fcs:
            is_track = event.uses_track_classification()
            athlete_fc = athlete.track_classification if is_track else athlete.field_classification
            if athlete_fc and athlete_fc not in event_fcs:
                fc_codes = ', '.join(fc.code for fc in event_fcs)
                raise serializers.ValidationError({'athlete': f'La clasificacion del atleta ({athlete_fc.code}) no corresponde a esta prueba ({fc_codes})'})
            if not athlete_fc:
                fc_codes = ', '.join(fc.code for fc in event_fcs)
                raise serializers.ValidationError({'athlete': f'Esta prueba requiere clasificacion funcional ({fc_codes})'})

        data['athlete_obj'] = athlete
        data['event_obj'] = event
        return data

    def create(self, validated_data):
        athlete = validated_data['athlete_obj']
        event = validated_data['event_obj']
        tournament = event.tournament
        registration = Registration.objects.filter(
            athlete=athlete,
            tournament=tournament,
            status__in=['approved', 'pending']
        ).order_by('-registered_at').first()
        athlete_event = AthleteEvent.objects.create(
            registration=registration,
            tournament_event=event,
            bib_number=None,
            lane=None,
        )
        return athlete_event


class AthleteEventSerializer(serializers.ModelSerializer):
    athlete_name = serializers.CharField(source='registration.athlete.user.get_full_name', read_only=True)
    athlete_id = serializers.UUIDField(source='registration.athlete.id', read_only=True)
    tournament_event_name = serializers.CharField(source='tournament_event.name', read_only=True)
    institution_name = serializers.CharField(source='registration.institution.name', read_only=True)
    classification_code = serializers.CharField(source='registration.athlete.functional_classification.code', read_only=True, default=None)
    track_classification_code = serializers.CharField(source='registration.athlete.track_classification.code', read_only=True, default=None)
    field_classification_code = serializers.CharField(source='registration.athlete.field_classification.code', read_only=True, default=None)
    sex_name = serializers.CharField(source='registration.athlete.sex.name', read_only=True, default=None)
    bib_number = serializers.IntegerField(required=False, allow_null=True)
    lane = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = AthleteEvent
        fields = ['id', 'registration', 'athlete_name', 'athlete_id', 'tournament_event', 'tournament_event_name', 'institution_name', 'classification_code', 'track_classification_code', 'field_classification_code', 'sex_name', 'bib_number', 'lane', 'status']
        read_only_fields = ['id']


class JudgeAssignmentSerializer(serializers.ModelSerializer):
    judge_name = serializers.CharField(source='judge.get_full_name', read_only=True)
    judge_email = serializers.CharField(source='judge.email', read_only=True)
    tournament_event_name = serializers.CharField(source='tournament_event.name', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.get_full_name', read_only=True)

    class Meta:
        model = JudgeAssignment
        fields = ['id', 'tournament_event', 'tournament_event_name', 'judge', 'judge_name', 'judge_email', 'is_head', 'assigned_by', 'assigned_by_name', 'assigned_at']
        read_only_fields = ['id', 'assigned_at']


class ResultSerializer(serializers.ModelSerializer):
    athlete_name = serializers.SerializerMethodField()
    recorded_by_name = serializers.CharField(source='recorded_by.get_full_name', read_only=True)

    class Meta:
        model = Result
        fields = [
            'id', 'athlete_event', 'athlete_name', 'attempt_number', 'value',
            'mark', 'is_valid', 'wind', 'notes', 'recorded_by', 'recorded_by_name', 'recorded_at'
        ]
        read_only_fields = ['id', 'recorded_at']

    def get_athlete_name(self, obj):
        return obj.athlete_event.registration.athlete.user.get_full_name()


class FinalResultSerializer(serializers.ModelSerializer):
    athlete_name = serializers.CharField(source='athlete.user.get_full_name', read_only=True)
    tournament_event_name = serializers.CharField(source='tournament_event.name', read_only=True)
    classification = serializers.SerializerMethodField()
    verified_by_name = serializers.CharField(source='verified_by.get_full_name', read_only=True)
    tournament_name = serializers.CharField(source='tournament_event.tournament.name', read_only=True)
    tournament_city = serializers.CharField(source='tournament_event.tournament.city', read_only=True)
    scheduled_date = serializers.DateTimeField(source='tournament_event.scheduled_date', read_only=True)
    event_type_name = serializers.CharField(source='tournament_event.event_type.name', read_only=True)
    is_track = serializers.SerializerMethodField()
    wind = serializers.SerializerMethodField()

    def get_is_track(self, obj):
        return bool(obj.tournament_event.event_type and obj.tournament_event.event_type.is_time_based)

    def get_classification(self, obj):
        """Clasificacion funcional segun el tipo de prueba: pista (T) usa track_classification,
        campo (F) usa field_classification; si no hay, cae a functional_classification."""
        a = obj.athlete
        if a is None:
            return None
        if self.get_is_track(obj):
            fc = a.track_classification or a.functional_classification
        else:
            fc = a.field_classification or a.functional_classification
        return fc.code if fc else None

    def get_wind(self, obj):
        ae = obj.tournament_event.athlete_events.filter(
            registration__athlete=obj.athlete,
            status='confirmed',
        ).first()
        if ae is None:
            return None
        res = ae.results.filter(attempt_number=1).first()
        return res.wind if res and res.wind is not None else None

    class Meta:
        model = FinalResult
        fields = [
            'id', 'tournament_event', 'tournament_event_name', 'tournament_name', 'tournament_city',
            'scheduled_date', 'event_type_name', 'is_track', 'athlete', 'athlete_name',
            'classification', 'rank', 'best_mark', 'points', 'record_type',
            'is_dnf', 'is_dns', 'is_dq', 'verified_by', 'verified_by_name', 'verified_at', 'wind'
        ]
        read_only_fields = ['id', 'verified_at']
