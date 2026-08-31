from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, RoleChoices


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    date_of_birth = serializers.DateField(required=False, write_only=True, allow_null=True)
    document_type = serializers.CharField(required=False, write_only=True, allow_blank=True)
    document_number = serializers.CharField(required=False, write_only=True, allow_blank=True)
    sex = serializers.UUIDField(required=False, write_only=True, allow_null=True)
    track_classification = serializers.UUIDField(required=False, write_only=True, allow_null=True)
    field_classification = serializers.UUIDField(required=False, write_only=True, allow_null=True)
    address_country = serializers.CharField(required=False, write_only=True, allow_blank=True)
    address_province = serializers.CharField(required=False, write_only=True, allow_blank=True)
    address_city = serializers.CharField(required=False, write_only=True, allow_blank=True)
    address_street = serializers.CharField(required=False, write_only=True, allow_blank=True)
    guardian_name = serializers.CharField(required=False, write_only=True, allow_blank=True)
    guardian_document_type = serializers.CharField(required=False, write_only=True, allow_blank=True)
    guardian_document_number = serializers.CharField(required=False, write_only=True, allow_blank=True)
    guardian_phone = serializers.CharField(required=False, write_only=True, allow_blank=True)
    guardian_email = serializers.EmailField(required=False, write_only=True, allow_blank=True)
    guardian_address_country = serializers.CharField(required=False, write_only=True, allow_blank=True)
    guardian_address_province = serializers.CharField(required=False, write_only=True, allow_blank=True)
    guardian_address_city = serializers.CharField(required=False, write_only=True, allow_blank=True)
    guardian_address_street = serializers.CharField(required=False, write_only=True, allow_blank=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'phone', 'role', 'password', 'password_confirm',
            'date_of_birth', 'document_type', 'document_number', 'sex',
            'track_classification', 'field_classification',
            'address_country', 'address_province', 'address_city', 'address_street',
            'guardian_name', 'guardian_document_type', 'guardian_document_number',
            'guardian_phone', 'guardian_email',
            'guardian_address_country', 'guardian_address_province',
            'guardian_address_city', 'guardian_address_street',
        ]
        read_only_fields = ['id']

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Las contraseñas no coinciden'})

        role = data.get('role', 'athlete')
        if role == RoleChoices.ATHLETE:
            date_of_birth = data.get('date_of_birth')
            if not date_of_birth:
                raise serializers.ValidationError({'date_of_birth': 'La fecha de nacimiento es obligatoria para atletas'})
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

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        role = validated_data.get('role', RoleChoices.ATHLETE)

        athlete_fields = {}
        if role == RoleChoices.ATHLETE:
            athlete_field_names = [
                'date_of_birth', 'document_type', 'document_number', 'sex',
                'track_classification', 'field_classification',
                'address_country', 'address_province', 'address_city', 'address_street',
                'guardian_name', 'guardian_document_type', 'guardian_document_number',
                'guardian_phone', 'guardian_email',
                'guardian_address_country', 'guardian_address_province',
                'guardian_address_city', 'guardian_address_street',
            ]
            for fname in athlete_field_names:
                if fname in validated_data:
                    athlete_fields[fname] = validated_data.pop(fname)

        user = User.objects.create_user(**validated_data)

        if role == RoleChoices.ATHLETE and athlete_fields:
            from paratletismo_core.tournaments.models import Athlete
            sex_id = athlete_fields.pop('sex', None)
            track_id = athlete_fields.pop('track_classification', None)
            field_id = athlete_fields.pop('field_classification', None)
            athlete = Athlete.objects.create(
                user=user,
                sex_id=sex_id,
                track_classification_id=track_id,
                field_classification_id=field_id,
                **athlete_fields
            )

        return user


class UserSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'phone', 'role', 'role_display', 'is_active', 'date_joined', 'avatar']
        read_only_fields = ['id', 'date_joined']


class UserUpdateSerializer(serializers.ModelSerializer):
    role_display = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'phone', 'role', 'role_display', 'avatar', 'is_active']
        read_only_fields = ['id', 'email', 'role', 'is_active']

    def get_role_display(self, obj):
        return obj.get_role_display()


class AdminUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'phone', 'role', 'is_active', 'date_joined', 'password']
        read_only_fields = ['id', 'date_joined']

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        instance = super().update(instance, validated_data)
        if password:
            instance.set_password(password)
            instance.save()
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    new_password_confirm = serializers.CharField(required=True, min_length=8)

    def validate(self, data):
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': 'Las contraseñas no coinciden'})
        return data
