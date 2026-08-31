from rest_framework import serializers
from .models import Institution, InstitutionUser, Coach, Athlete, Tournament, TournamentEvent, OrganizationPayment
from paratletismo_core.config.models import Sex, Category, FunctionalClassification
from paratletismo_core.users.models import User


class InstitutionSerializer(serializers.ModelSerializer):
    athlete_count = serializers.SerializerMethodField()
    coach_count = serializers.SerializerMethodField()

    class Meta:
        model = Institution
        fields = '__all__'
        read_only_fields = ['id', 'name', 'short_name', 'email', 'can_organize', 'organized_until', 'created_at', 'updated_at']

    def get_athlete_count(self, obj):
        return obj.athletes.count()

    def get_coach_count(self, obj):
        return obj.coaches.count()


class InstitutionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Institution
        fields = ['name', 'short_name', 'description', 'address', 'city', 'province', 'phone', 'email', 'website', 'founded_date', 'logo']
        extra_kwargs = {
            'name': {'required': False, 'allow_blank': True},
            'short_name': {'required': False, 'allow_blank': True},
            'email': {'required': False, 'allow_blank': True},
        }


class InstitutionManageSerializer(serializers.ModelSerializer):
    """Serializer for superadmin to manage institution organizer permissions."""
    class Meta:
        model = Institution
        fields = ['id', 'name', 'short_name', 'is_active', 'can_organize', 'organized_until', 'email', 'phone', 'city', 'province']


class OrganizationPaymentSerializer(serializers.ModelSerializer):
    institution_name = serializers.CharField(source='institution.name', read_only=True)
    paid_by_name = serializers.CharField(source='paid_by.get_full_name', read_only=True)

    class Meta:
        model = OrganizationPayment
        fields = '__all__'
        read_only_fields = ['id', 'payment_date', 'paid_by']

    def validate(self, attrs):
        if attrs.get('valid_until') and attrs.get('valid_from') and attrs['valid_until'] <= attrs['valid_from']:
            raise serializers.ValidationError('valid_until debe ser posterior a valid_from')
        return attrs


class InstitutionUserSerializer(serializers.ModelSerializer):
    institution_name = serializers.CharField(source='institution.name', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = InstitutionUser
        fields = ['id', 'institution', 'institution_name', 'user', 'user_name', 'position', 'created_at']
        read_only_fields = ['id', 'created_at']


class CoachSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    institution_name = serializers.CharField(source='institution.name', read_only=True)
    athlete_count = serializers.SerializerMethodField()

    class Meta:
        model = Coach
        fields = ['id', 'user', 'user_name', 'user_email', 'institution', 'institution_name', 'document_type', 'document_number', 'specialties', 'license_number', 'athlete_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_athlete_count(self, obj):
        return obj.athletes.count()


class CoachCreateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(write_only=True, max_length=100)
    last_name = serializers.CharField(write_only=True, max_length=100)
    phone = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Coach
        fields = ['institution', 'document_type', 'document_number', 'specialties', 'license_number', 'email', 'password', 'first_name', 'last_name', 'phone']
        extra_kwargs = {
            'institution': {'required': False, 'allow_null': True},
        }

    def _resolve_institution(self, validated_data):
        institution = validated_data.get('institution')
        if institution:
            return validated_data
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            user = request.user
            iu = InstitutionUser.objects.filter(user=user).first()
            if iu:
                institution = iu.institution
            else:
                coach = Coach.objects.filter(user=user, institution__isnull=False).first()
                if coach:
                    institution = coach.institution
            if not institution:
                raise serializers.ValidationError({'institution': 'No tenes una institucion vinculada. Completa los datos de tu institucion en Mi Perfil.'})
            validated_data['institution'] = institution
        return validated_data

    def create(self, validated_data):
        email = validated_data.pop('email')
        password = validated_data.pop('password')
        first_name = validated_data.pop('first_name')
        last_name = validated_data.pop('last_name')
        phone = validated_data.pop('phone', '')

        validated_data = self._resolve_institution(validated_data)

        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            role='coach'
        )
        return Coach.objects.create(user=user, **validated_data)


class AthleteSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    institution_name = serializers.CharField(source='institution.name', read_only=True)
    coach_name = serializers.SerializerMethodField()
    sex_name = serializers.CharField(source='sex.name', read_only=True)
    classification_code = serializers.CharField(source='functional_classification.code', read_only=True)
    classification_name = serializers.CharField(source='functional_classification.name', read_only=True)
    track_classification_code = serializers.CharField(source='track_classification.code', read_only=True, default=None)
    track_classification_name = serializers.CharField(source='track_classification.name', read_only=True, default=None)
    field_classification_code = serializers.CharField(source='field_classification.code', read_only=True, default=None)
    field_classification_name = serializers.CharField(source='field_classification.name', read_only=True, default=None)
    age = serializers.ReadOnlyField()
    is_minor = serializers.ReadOnlyField()
    user_phone = serializers.CharField(source='user.phone', read_only=True)

    class Meta:
        model = Athlete
        fields = [
            'id', 'user', 'user_name', 'user_email', 'user_phone',
            'institution', 'institution_name',
            'coach', 'coach_name', 'document_type', 'document_number', 'date_of_birth', 'age', 'is_minor',
            'sex', 'sex_name',
            'functional_classification', 'classification_code', 'classification_name',
            'track_classification', 'track_classification_code', 'track_classification_name',
            'field_classification', 'field_classification_code', 'field_classification_name',
            'classification_status', 'classification_notes', 'classified_by',
            'classification_date', 'phone', 'emergency_contact', 'emergency_phone',
            'medical_info',
            'address_country', 'address_province', 'address_city', 'address_street',
            'guardian_name', 'guardian_document_type', 'guardian_document_number',
            'guardian_phone', 'guardian_email',
            'guardian_address_country', 'guardian_address_province',
                'guardian_address_city', 'guardian_address_street',
                'profile_image', 'cud_file',
                'created_at', 'updated_at'
            ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def get_coach_name(self, obj):
        return obj.coach.user.get_full_name() if obj.coach else None


class AthleteCreateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(write_only=True, max_length=100)
    last_name = serializers.CharField(write_only=True, max_length=100)
    phone = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Athlete
        fields = [
            'institution', 'coach', 'document_type', 'document_number',
            'email', 'password', 'first_name', 'last_name', 'phone',
            'date_of_birth', 'sex',
            'functional_classification', 'track_classification', 'field_classification',
            'emergency_contact', 'emergency_phone', 'medical_info',
            'address_country', 'address_province', 'address_city', 'address_street',
            'guardian_name', 'guardian_document_type', 'guardian_document_number',
            'guardian_phone', 'guardian_email',
            'guardian_address_country', 'guardian_address_province',
            'guardian_address_city', 'guardian_address_street',
            'profile_image', 'cud_file',
        ]
        extra_kwargs = {
            'institution': {'required': False, 'allow_null': True},
        }

    def validate(self, data):
        date_of_birth = data.get('date_of_birth')
        if date_of_birth:
            from datetime import date
            today = date.today()
            age = today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
            if age <= 17:
                if not data.get('guardian_name'):
                    raise serializers.ValidationError({'guardian_name': 'El nombre del adulto responsable es obligatorio para menores de 18 anos'})
                if not data.get('guardian_document_number'):
                    raise serializers.ValidationError({'guardian_document_number': 'El documento del adulto responsable es obligatorio para menores de 18 anos'})
                if not data.get('guardian_phone'):
                    raise serializers.ValidationError({'guardian_phone': 'El telefono del adulto responsable es obligatorio para menores de 18 anos'})
        return data

    def _resolve_institution(self, validated_data):
        institution = validated_data.get('institution')
        if institution:
            return validated_data
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            user = request.user
            iu = InstitutionUser.objects.filter(user=user).first()
            if iu:
                institution = iu.institution
            else:
                coach = Coach.objects.filter(user=user, institution__isnull=False).first()
                if coach:
                    institution = coach.institution
            if not institution:
                raise serializers.ValidationError({'institution': 'No tenes una institucion vinculada. Completa los datos de tu institucion en Mi Perfil.'})
            validated_data['institution'] = institution
        return validated_data

    def create(self, validated_data):
        email = validated_data.pop('email')
        password = validated_data.pop('password')
        first_name = validated_data.pop('first_name')
        last_name = validated_data.pop('last_name')
        phone = validated_data.pop('phone', '')

        validated_data = self._resolve_institution(validated_data)

        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            role='athlete'
        )
        return Athlete.objects.create(user=user, **validated_data)


class AthleteUpdateSerializer(AthleteSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, min_length=8)

    class Meta(AthleteSerializer.Meta):
        fields = AthleteSerializer.Meta.fields + ['password']

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        if password:
            instance.user.set_password(password)
            instance.user.save()
        return super().update(instance, validated_data)


class TournamentSerializer(serializers.ModelSerializer):
    organizer_name = serializers.SerializerMethodField()
    admin_name = serializers.CharField(source='admin_user.get_full_name', read_only=True)
    disciplines_list = serializers.StringRelatedField(many=True, source='disciplines')
    sexes_list = serializers.StringRelatedField(many=True, source='sexes')
    categories_list = serializers.StringRelatedField(many=True, source='categories')
    functional_classifications_list = serializers.StringRelatedField(many=True, source='functional_classifications')
    participant_count = serializers.SerializerMethodField()
    event_count = serializers.SerializerMethodField()
    payment_status_label = serializers.SerializerMethodField()
    has_marks = serializers.SerializerMethodField()

    class Meta:
        model = Tournament
        fields = [
            'id', 'name', 'description', 'organizer', 'organizer_name', 'admin_user',
            'admin_name', 'venue', 'address', 'city', 'province', 'status',
            'payment_status', 'payment_status_label', 'payment_amount', 'payment_date',
            'payment_notes', 'paid_by',
            'registration_opens', 'registration_closes', 'tournament_start', 'tournament_end',
            'registration_fee', 'max_participants', 'max_events_per_athlete',
            'head_judge', 'disciplines', 'sexes', 'categories', 'functional_classifications',
            'disciplines_list', 'sexes_list', 'categories_list', 'functional_classifications_list', 'logo', 'rules', 'use_bibs',
            'participant_count', 'event_count', 'is_active', 'has_marks', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'payment_status', 'payment_amount', 'payment_date', 'payment_notes', 'paid_by']

    def get_payment_status_label(self, obj):
        return dict(Tournament.PAYMENT_STATUS_CHOICES).get(obj.payment_status, obj.payment_status)

    def get_organizer_name(self, obj):
        return obj.organizer.name if obj.organizer else ''

    def get_has_marks(self, obj):
        if getattr(obj, 'marks_count', None) is not None:
            return obj.marks_count > 0
        from paratletismo_core.competitions.models import FinalResult, Result
        return (
            FinalResult.objects.filter(tournament_event__tournament=obj).exists()
            or Result.objects.filter(athlete_event__tournament_event__tournament=obj).exists()
        )

    def get_participant_count(self, obj):
        from paratletismo_core.competitions.models import Registration
        return Registration.objects.filter(tournament=obj).values('athlete').distinct().count()

    def get_event_count(self, obj):
        return obj.events.count()

    def update(self, instance, validated_data):
        m2m_fields = ['disciplines', 'sexes', 'categories', 'functional_classifications']
        m2m_data = {field: validated_data.pop(field, None) for field in m2m_fields}
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        for field, value in m2m_data.items():
            if value is not None:
                getattr(instance, field).set(value)
        return instance


class TournamentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tournament
        fields = [
            'name', 'description', 'venue', 'address', 'city', 'province',
            'registration_opens', 'registration_closes', 'tournament_start', 'tournament_end',
            'registration_fee', 'max_participants', 'max_events_per_athlete',
            'logo', 'rules', 'use_bibs'
        ]

    def create(self, validated_data):
        from datetime import datetime, timezone
        validated_data['admin_user'] = self.context['request'].user
        user = self.context['request'].user
        from paratletismo_core.users.models import RoleChoices
        if user.role in (RoleChoices.SUPERADMIN, RoleChoices.ADMIN):
            validated_data['payment_status'] = 'paid'
            validated_data['paid_by'] = user
            validated_data['payment_date'] = datetime.now(timezone.utc)
        else:
            validated_data['payment_status'] = 'pending'
        organizer_id = self.initial_data.get('organizer')
        if organizer_id:
            try:
                validated_data['organizer'] = Institution.objects.get(id=organizer_id)
            except (Institution.DoesNotExist, ValueError):
                raise serializers.ValidationError({'organizer': 'La institucion seleccionada no existe'})
        return Tournament.objects.create(**validated_data)


class TournamentEventCardSerializer(serializers.ModelSerializer):
    event_type_name = serializers.CharField(source='event_type.name', read_only=True)
    discipline_name = serializers.CharField(source='discipline.name', read_only=True)
    sex_name = serializers.CharField(source='sex.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    classification_code = serializers.CharField(source='functional_classification.code', read_only=True)
    sexes_list = serializers.StringRelatedField(many=True, source='sexes', read_only=True)
    categories_list = serializers.StringRelatedField(many=True, source='categories', read_only=True)
    classifications_list = serializers.StringRelatedField(many=True, source='functional_classifications', read_only=True)
    athlete_count = serializers.SerializerMethodField()
    result_count = serializers.SerializerMethodField()

    def get_athlete_count(self, obj):
        return obj.athlete_events.exclude(status='withdrawn').count()

    def get_result_count(self, obj):
        from paratletismo_core.competitions.models import FinalResult
        return FinalResult.objects.filter(tournament_event=obj).count()

    class Meta:
        model = TournamentEvent
        fields = [
            'id', 'name', 'event_type_name', 'discipline_name', 'sex_name', 'category_name',
            'classification_code', 'sexes_list', 'categories_list', 'classifications_list',
            'scheduled_date', 'scheduled_time', 'status', 'is_final', 'athlete_count', 'result_count'
        ]


class InstitutionTournamentSerializer(serializers.ModelSerializer):
    organizer_name = serializers.SerializerMethodField()
    admin_name = serializers.CharField(source='admin_user.get_full_name', read_only=True)
    disciplines_list = serializers.StringRelatedField(many=True, source='disciplines', read_only=True)
    sexes_list = serializers.StringRelatedField(many=True, source='sexes', read_only=True)
    categories_list = serializers.StringRelatedField(many=True, source='categories', read_only=True)
    functional_classifications_list = serializers.StringRelatedField(many=True, source='functional_classifications', read_only=True)
    payment_status_label = serializers.SerializerMethodField()
    participant_count = serializers.SerializerMethodField()
    event_count = serializers.SerializerMethodField()
    events = TournamentEventCardSerializer(many=True, read_only=True)

    class Meta:
        model = Tournament
        fields = [
            'id', 'name', 'description', 'venue', 'address', 'city', 'province', 'status',
            'payment_status', 'payment_status_label', 'payment_amount', 'payment_date',
            'tournament_start', 'tournament_end', 'registration_opens', 'registration_closes',
            'registration_fee', 'max_participants', 'max_events_per_athlete',
            'is_active', 'use_bibs', 'organizer_name', 'admin_name',
            'disciplines_list', 'sexes_list', 'categories_list', 'functional_classifications_list',
            'participant_count', 'event_count', 'events'
        ]
        read_only_fields = fields

    def get_payment_status_label(self, obj):
        return dict(Tournament.PAYMENT_STATUS_CHOICES).get(obj.payment_status, obj.payment_status)

    def get_organizer_name(self, obj):
        return obj.organizer.name if obj.organizer else ''

    def get_participant_count(self, obj):
        from paratletismo_core.competitions.models import Registration
        return Registration.objects.filter(tournament=obj).values('athlete').distinct().count()

    def get_event_count(self, obj):
        return obj.events.count()


class TournamentEventSerializer(serializers.ModelSerializer):
    tournament_name = serializers.CharField(source='tournament.name', read_only=True)
    event_type_name = serializers.CharField(source='event_type.name', read_only=True)
    discipline_name = serializers.CharField(source='discipline.name', read_only=True)
    sex_name = serializers.CharField(source='sex.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    classification_code = serializers.CharField(source='functional_classification.code', read_only=True)
    sexes_list = serializers.StringRelatedField(many=True, source='sexes', read_only=True)
    categories_list = serializers.StringRelatedField(many=True, source='categories', read_only=True)
    classifications_list = serializers.StringRelatedField(many=True, source='functional_classifications', read_only=True)
    athlete_count = serializers.SerializerMethodField()
    is_track = serializers.SerializerMethodField()

    def get_athlete_count(self, obj):
        return getattr(obj, 'athlete_count', None) or obj.athlete_events.exclude(status='withdrawn').count()

    def get_is_track(self, obj):
        return bool(obj.event_type and obj.event_type.is_time_based)

    class Meta:
        model = TournamentEvent
        fields = [
            'id', 'tournament', 'tournament_name', 'name', 'event_type', 'event_type_name',
            'discipline', 'discipline_name', 'sex', 'sex_name', 'category', 'category_name',
            'functional_classification', 'classification_code',
            'sexes', 'sexes_list', 'categories', 'categories_list',
            'functional_classifications', 'classifications_list',
            'scheduled_date', 'scheduled_time', 'call_time', 'venue_detail', 'is_final', 'status', 'created_at',
            'athlete_count', 'is_track'
        ]
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        sexes = validated_data.pop('sexes', [])
        categories = validated_data.pop('categories', [])
        functional_classifications = validated_data.pop('functional_classifications', [])
        sex = validated_data.pop('sex', None)
        category = validated_data.pop('category', None)
        functional_classification = validated_data.pop('functional_classification', None)
        event = TournamentEvent.objects.create(**validated_data)
        if sex:
            event.sex = sex
            if sex not in sexes:
                sexes.append(sex)
        if category:
            event.category = category
            if category not in categories:
                categories.append(category)
        if functional_classification:
            event.functional_classification = functional_classification
            if functional_classification not in functional_classifications:
                functional_classifications.append(functional_classification)
        event.sexes.set(sexes)
        event.categories.set(categories)
        if functional_classifications:
            event.functional_classifications.set(functional_classifications)
            if not event.functional_classification:
                event.functional_classification = functional_classifications[0]
        event.save()
        return event

    def update(self, instance, validated_data):
        sexes = validated_data.pop('sexes', None)
        categories = validated_data.pop('categories', None)
        functional_classifications = validated_data.pop('functional_classifications', None)
        sex = validated_data.pop('sex', None)
        category = validated_data.pop('category', None)
        functional_classification = validated_data.pop('functional_classification', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if sex is not None:
            instance.sex = sex
        if category is not None:
            instance.category = category
        if functional_classification is not None:
            instance.functional_classification = functional_classification
        if sexes is not None:
            instance.sexes.set(sexes)
        if categories is not None:
            instance.categories.set(categories)
        if functional_classifications is not None:
            instance.functional_classifications.set(functional_classifications)
        instance.save()
        return instance


class TournamentEventBulkCreateSerializer(serializers.Serializer):
    event_types = serializers.ListField(child=serializers.UUIDField(), write_only=True, required=False)
    sexes = serializers.ListField(child=serializers.UUIDField(), write_only=True, required=False)
    categories = serializers.ListField(child=serializers.UUIDField(), write_only=True, required=False)
    functional_classifications = serializers.ListField(child=serializers.UUIDField(), required=False, allow_empty=True, write_only=True)
    groups = serializers.ListField(child=serializers.DictField(), required=False, write_only=True)
    combos = serializers.ListField(child=serializers.DictField(), required=False, write_only=True)
    scheduled_date = serializers.DateTimeField(required=False, allow_null=True)
    scheduled_time = serializers.TimeField(required=False, allow_null=True)
    call_time = serializers.TimeField(required=False, allow_null=True)
    venue_detail = serializers.CharField(required=False, allow_blank=True)
    tournament = serializers.UUIDField()

    def validate(self, attrs):
        combos = attrs.get('combos')
        groups = attrs.get('groups')
        if combos is not None:
            if not combos:
                raise serializers.ValidationError({'combos': 'Debes enviar al menos una prueba'})
            for i, combo in enumerate(combos):
                if not combo.get('event_type') or not combo.get('sex') or not combo.get('category'):
                    raise serializers.ValidationError({'combos': f'La prueba {i + 1} debe tener disciplina, sexo y categoria'})
        elif groups is not None:
            if not groups:
                raise serializers.ValidationError({'groups': 'Debes agregar al menos un grupo de pruebas'})
            for i, g in enumerate(groups):
                if not g.get('event_types') or not g.get('sexes') or not g.get('categories'):
                    raise serializers.ValidationError({'groups': f'El grupo {i + 1} debe tener al menos una disciplina, sexo y categoria'})
        else:
            if not attrs.get('event_types') or not attrs.get('sexes') or not attrs.get('categories'):
                raise serializers.ValidationError('Debes seleccionar al menos una disciplina, sexo y categoria')
        return attrs

    def save(self, **kwargs):
        return self.create(self.validated_data)

    def create(self, validated_data):
        from itertools import product
        from paratletismo_core.config.models import EventType as EventTypeModel

        tournament_id = validated_data.pop('tournament')
        combos = validated_data.pop('combos', None)

        if combos is None:
            groups = validated_data.pop('groups', None)
            if groups is None:
                groups = [{
                    'event_types': validated_data.pop('event_types', []),
                    'sexes': validated_data.pop('sexes', []),
                    'categories': validated_data.pop('categories', []),
                    'functional_classifications': validated_data.pop('functional_classifications', []),
                }]
            combos = []
            for group in groups:
                et_ids = group.get('event_types', [])
                sex_ids = group.get('sexes', [])
                cat_ids = group.get('categories', [])
                fc_ids = group.get('functional_classifications', [])
                if fc_ids:
                    for et_id, sex_id, cat_id, fc_id in product(et_ids, sex_ids, cat_ids, fc_ids):
                        combos.append({'event_type': et_id, 'sex': sex_id, 'category': cat_id, 'functional_classification': fc_id})
                else:
                    for et_id, sex_id, cat_id in product(et_ids, sex_ids, cat_ids):
                        combos.append({'event_type': et_id, 'sex': sex_id, 'category': cat_id, 'functional_classification': None})

        schedule_fields = {}
        for field in ['scheduled_date', 'scheduled_time', 'call_time', 'venue_detail']:
            if field in validated_data:
                schedule_fields[field] = validated_data[field]

        et_ids = {c['event_type'] for c in combos}
        sex_ids = {c['sex'] for c in combos}
        cat_ids = {c['category'] for c in combos}
        fc_ids = {c['functional_classification'] for c in combos if c.get('functional_classification')}

        ets = {str(k): v for k, v in EventTypeModel.objects.in_bulk(et_ids).items()}
        sexs = {str(k): v for k, v in Sex.objects.in_bulk(sex_ids).items()}
        cats = {str(k): v for k, v in Category.objects.in_bulk(cat_ids).items()}
        fcs = {str(k): v for k, v in FunctionalClassification.objects.in_bulk(fc_ids).items()}

        event_objects = []
        for combo in combos:
            event_type = ets[combo['event_type']]
            sex = sexs.get(combo['sex'])
            cat = cats.get(combo['category'])
            fc = fcs.get(combo['functional_classification']) if combo.get('functional_classification') else None

            parts = [event_type.name]
            if sex: parts.append(sex.name)
            if cat: parts.append(cat.name)
            if fc: parts.append(fc.code)
            name = ' - '.join(parts)

            event_objects.append(TournamentEvent(
                tournament_id=tournament_id,
                name=name,
                event_type=event_type,
                discipline=event_type.discipline,
                sex=sex,
                category=cat,
                functional_classification=fc,
                **schedule_fields
            ))

        created_events = TournamentEvent.objects.bulk_create(event_objects)

        sex_through = TournamentEvent.sexes.through
        cat_through = TournamentEvent.categories.through
        fc_through = TournamentEvent.functional_classifications.through

        sex_rows = [
            sex_through(tournamentevent_id=e.id, sex_id=combo['sex'])
            for e, combo in zip(created_events, combos) if combo['sex']
        ]
        cat_rows = [
            cat_through(tournamentevent_id=e.id, category_id=combo['category'])
            for e, combo in zip(created_events, combos) if combo['category']
        ]
        fc_rows = [
            fc_through(tournamentevent_id=e.id, functionalclassification_id=combo['functional_classification'])
            for e, combo in zip(created_events, combos) if combo.get('functional_classification')
        ]

        if sex_rows:
            sex_through.objects.bulk_create(sex_rows)
        if cat_rows:
            cat_through.objects.bulk_create(cat_rows)
        if fc_rows:
            fc_through.objects.bulk_create(fc_rows)

        return created_events
