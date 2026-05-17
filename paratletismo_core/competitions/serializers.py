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
            'registered_by', 'registered_by_name', 'registered_at', 'notes'
        ]
        read_only_fields = ['id', 'registered_at']


class RegistrationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Registration
        fields = ['tournament', 'athlete', 'notes']

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

        if athlete.sex and event.sex and athlete.sex.id != event.sex.id:
            raise serializers.ValidationError({'athlete': f'El sexo del atleta no corresponde a esta prueba ({event.sex.name} requerido)'})

        if athlete.sex and event.category:
            from paratletismo_core.tournaments.models import Category
            cat = event.category
            age = athlete.age
            if cat.min_age and age < cat.min_age:
                raise serializers.ValidationError({'athlete': f'El atleta no tiene la edad minima para categoria {cat.name} (min {cat.min_age})'})
            if cat.max_age and age > cat.max_age:
                raise serializers.ValidationError({'athlete': f'El atleta supera la edad maxima para categoria {cat.name} (max {cat.max_age})'})

        if athlete.functional_classification and event.functional_classification:
            if athlete.functional_classification.id != event.functional_classification.id:
                raise serializers.ValidationError({'athlete': f'La clasificacion funcional {athlete.functional_classification.code} no corresponde a esta prueba ({event.functional_classification.code} requerida)'})

        if event.functional_classification and not athlete.functional_classification:
            raise serializers.ValidationError({'athlete': f'Esta prueba requiere clasificacion funcional {event.functional_classification.code}'})

        data['athlete_obj'] = athlete
        data['event_obj'] = event
        return data

    def create(self, validated_data):
        athlete = validated_data['athlete_obj']
        event = validated_data['event_obj']
        tournament = event.tournament
        athlete_event = AthleteEvent.objects.create(
            registration_id=validated_data.get('registration_id'),
            tournament_event=event,
            bib_number=None,
            lane=None,
        )
        return athlete_event


class AthleteEventSerializer(serializers.ModelSerializer):
    athlete_name = serializers.CharField(source='registration.athlete.user.get_full_name', read_only=True)
    tournament_event_name = serializers.CharField(source='tournament_event.name', read_only=True)

    class Meta:
        model = AthleteEvent
        fields = ['id', 'registration', 'athlete_name', 'tournament_event', 'tournament_event_name', 'bib_number', 'lane']
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
    classification = serializers.CharField(source='athlete.functional_classification.code', read_only=True)
    verified_by_name = serializers.CharField(source='verified_by.get_full_name', read_only=True)

    class Meta:
        model = FinalResult
        fields = [
            'id', 'tournament_event', 'tournament_event_name', 'athlete', 'athlete_name',
            'classification', 'rank', 'best_mark', 'points', 'record_type',
            'is_dnf', 'is_dns', 'is_dq', 'verified_by', 'verified_by_name', 'verified_at'
        ]
        read_only_fields = ['id', 'verified_at']
