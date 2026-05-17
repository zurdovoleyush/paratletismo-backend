from rest_framework import serializers
from .models import Institution, InstitutionUser, Coach, Athlete, Tournament, TournamentEvent
from paratletismo_core.users.models import User


class InstitutionSerializer(serializers.ModelSerializer):
    athlete_count = serializers.SerializerMethodField()
    coach_count = serializers.SerializerMethodField()

    class Meta:
        model = Institution
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_athlete_count(self, obj):
        return obj.athletes.count()

    def get_coach_count(self, obj):
        return obj.coaches.count()


class InstitutionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Institution
        fields = ['name', 'short_name', 'description', 'address', 'city', 'province', 'phone', 'email', 'website', 'founded_date', 'logo']


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

    def create(self, validated_data):
        email = validated_data.pop('email')
        password = validated_data.pop('password')
        first_name = validated_data.pop('first_name')
        last_name = validated_data.pop('last_name')
        phone = validated_data.pop('phone', '')

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
    age = serializers.ReadOnlyField()

    class Meta:
        model = Athlete
        fields = [
            'id', 'user', 'user_name', 'user_email', 'institution', 'institution_name',
            'coach', 'coach_name', 'document_type', 'document_number', 'date_of_birth', 'age', 'sex', 'sex_name',
            'functional_classification', 'classification_code', 'classification_name',
            'classification_status', 'classification_notes', 'classified_by',
            'classification_date', 'emergency_contact', 'emergency_phone',
            'medical_info', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_coach_name(self, obj):
        return str(obj.user) if obj.coach else None


class AthleteCreateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(write_only=True, max_length=100)
    last_name = serializers.CharField(write_only=True, max_length=100)
    phone = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Athlete
        fields = [
            'institution', 'coach', 'document_type', 'document_number', 'email', 'password', 'first_name', 'last_name', 'phone',
            'date_of_birth', 'sex', 'functional_classification', 'emergency_contact',
            'emergency_phone', 'medical_info'
        ]

    def create(self, validated_data):
        email = validated_data.pop('email')
        password = validated_data.pop('password')
        first_name = validated_data.pop('first_name')
        last_name = validated_data.pop('last_name')
        phone = validated_data.pop('phone', '')

        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            role='athlete'
        )
        return Athlete.objects.create(user=user, **validated_data)


class TournamentSerializer(serializers.ModelSerializer):
    organizer_name = serializers.CharField(source='organizer.name', read_only=True)
    admin_name = serializers.CharField(source='admin_user.get_full_name', read_only=True)
    disciplines_list = serializers.StringRelatedField(many=True, source='disciplines')
    sexes_list = serializers.StringRelatedField(many=True, source='sexes')
    categories_list = serializers.StringRelatedField(many=True, source='categories')
    participant_count = serializers.SerializerMethodField()
    event_count = serializers.SerializerMethodField()

    class Meta:
        model = Tournament
        fields = [
            'id', 'name', 'description', 'organizer', 'organizer_name', 'admin_user',
            'admin_name', 'venue', 'address', 'city', 'province', 'status',
            'registration_opens', 'registration_closes', 'tournament_start', 'tournament_end',
            'registration_fee', 'max_participants', 'disciplines', 'sexes', 'categories',
            'disciplines_list', 'sexes_list', 'categories_list', 'logo', 'rules',
            'participant_count', 'event_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_participant_count(self, obj):
        from paratletismo_core.competitions.models import Registration
        return Registration.objects.filter(tournament=obj).values('athlete').distinct().count()

    def get_event_count(self, obj):
        return obj.events.count()


class TournamentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tournament
        fields = [
            'name', 'description', 'venue', 'address', 'city', 'province',
            'registration_opens', 'registration_closes', 'tournament_start', 'tournament_end',
            'registration_fee', 'max_participants', 'disciplines', 'sexes', 'categories',
            'logo', 'rules'
        ]
        extra_kwargs = {
            'disciplines': {'required': False, 'allow_empty': True},
            'sexes': {'required': False, 'allow_empty': True},
            'categories': {'required': False, 'allow_empty': True},
        }

    def to_internal_value(self, data):
        ret = super().to_internal_value(data)
        for field in ['disciplines', 'sexes', 'categories']:
            if not ret.get(field):
                ret[field] = []
        return ret

    def create(self, validated_data):
        disciplines = validated_data.pop('disciplines', None)
        sexes = validated_data.pop('sexes', None)
        categories = validated_data.pop('categories', None)
        validated_data['admin_user'] = self.context['request'].user
        try:
            institution = InstitutionUser.objects.get(user=self.context['request'].user).institution
        except InstitutionUser.DoesNotExist:
            raise serializers.ValidationError({'organizer': 'Debes registrar tu institucion primero'})
        validated_data['organizer'] = institution
        tournament = Tournament.objects.create(**validated_data)
        if disciplines is not None:
            tournament.disciplines.set(disciplines)
        if sexes is not None:
            tournament.sexes.set(sexes)
        if categories is not None:
            tournament.categories.set(categories)
        return tournament


class TournamentEventSerializer(serializers.ModelSerializer):
    tournament_name = serializers.CharField(source='tournament.name', read_only=True)
    event_type_name = serializers.CharField(source='event_type.name', read_only=True)
    discipline_name = serializers.CharField(source='discipline.name', read_only=True)
    sex_name = serializers.CharField(source='sex.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    classification_code = serializers.CharField(source='functional_classification.code', read_only=True)

    class Meta:
        model = TournamentEvent
        fields = [
            'id', 'tournament', 'tournament_name', 'name', 'event_type', 'event_type_name',
            'discipline', 'discipline_name', 'sex', 'sex_name', 'category', 'category_name',
            'functional_classification', 'classification_code', 'scheduled_date',
            'scheduled_time', 'venue_detail', 'status', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class TournamentEventBulkCreateSerializer(serializers.Serializer):
    event_types = serializers.ListField(child=serializers.UUIDField(), write_only=True)
    sexes = serializers.ListField(child=serializers.UUIDField(), write_only=True)
    categories = serializers.ListField(child=serializers.UUIDField(), write_only=True)
    functional_classifications = serializers.ListField(child=serializers.UUIDField(), required=False, allow_empty=True, write_only=True)
    scheduled_date = serializers.DateTimeField()
    scheduled_time = serializers.TimeField(required=False, allow_null=True)
    venue_detail = serializers.CharField(required=False, allow_blank=True)
    tournament = serializers.UUIDField()

    def save(self, **kwargs):
        return self.create(self.validated_data)

    def create(self, validated_data):
        from itertools import product
        from paratletismo_core.config.models import EventType as EventTypeModel, FunctionalClassification as FCModel

        tournament_id = validated_data.pop('tournament')
        fc_list = validated_data.pop('functional_classifications', [])
        event_types = validated_data.pop('event_types')
        sex_list = validated_data.pop('sexes')
        cat_list = validated_data.pop('categories')

        fc_ids = fc_list if fc_list else [None]
        combos = list(product(event_types, sex_list, cat_list, fc_ids))

        created_events = []
        for et_id, sex_id, cat_id, fc_id in combos:
            event_type = EventTypeModel.objects.get(id=et_id)
            fc_name = ''
            if fc_id:
                fc = FCModel.objects.get(id=fc_id)
                fc_name = f" ({fc.code})"

            name = f"{event_type.name}{fc_name}"

            event = TournamentEvent.objects.create(
                tournament_id=tournament_id,
                name=name,
                event_type=event_type,
                discipline=event_type.discipline,
                sex_id=sex_id,
                category_id=cat_id,
                functional_classification_id=fc_id,
                **validated_data
            )
            created_events.append(event)
        return created_events
