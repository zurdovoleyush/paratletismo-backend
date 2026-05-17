from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from paratletismo_core.config.models import Discipline, Sex, Category, FunctionalClassification, EventType
from paratletismo_core.users.models import RoleChoices

User = get_user_model()


class Command(BaseCommand):
    help = 'Carga datos iniciales de configuracion'

    def handle(self, *args, **options):
        self.stdout.write('Creando superusuario...')
        if not User.objects.filter(email='admin@paratletismo.com').exists():
            User.objects.create_superuser(
                email='admin@paratletismo.com',
                password='admin123',
                first_name='Admin',
                last_name='Sistema',
            )
            self.stdout.write(self.style.SUCCESS('Superusuario creado'))

        self.stdout.write('Creando sexos...')
        sexes = [
            {'name': 'Masculino', 'code': 'M'},
            {'name': 'Femenino', 'code': 'F'},
        ]
        for sex_data in sexes:
            Sex.objects.get_or_create(**sex_data)
        self.stdout.write(self.style.SUCCESS(f'{len(sexes)} sexos creados'))

        self.stdout.write('Creando disciplinas...')
        disciplines_data = [
            {'name': 'Carreras', 'description': 'Pruebas de velocidad y medio fondo'},
            {'name': 'Saltos', 'description': 'Pruebas de salto en longitud y altura'},
            {'name': 'Lanzamientos', 'description': 'Pruebas de lanzamiento de peso, disco, jabalina'},
        ]
        disciplines = {}
        for d_data in disciplines_data:
            d, _ = Discipline.objects.get_or_create(**d_data)
            disciplines[d.name] = d
        self.stdout.write(self.style.SUCCESS(f'{len(disciplines)} disciplinas creadas'))

        self.stdout.write('Creando categorias...')
        categories_data = [
            {'name': 'Sub-14', 'description': 'Menores de 14 anos', 'min_age': None, 'max_age': 13},
            {'name': 'Sub-18', 'description': 'Menores de 18 anos', 'min_age': 14, 'max_age': 17},
            {'name': 'Sub-20', 'description': 'Menores de 20 anos', 'min_age': 18, 'max_age': 19},
            {'name': 'Senior', 'description': 'Mayores de 20 anos', 'min_age': 20, 'max_age': None},
            {'name': 'Master', 'description': 'Mayores de 35 anos', 'min_age': 35, 'max_age': None},
        ]
        for c_data in categories_data:
            Category.objects.get_or_create(**c_data)
        self.stdout.write(self.style.SUCCESS(f'{len(categories_data)} categorias creadas'))

        self.stdout.write('Creando clasificaciones funcionales...')
        classifications_data = [
            {'code': 'T11', 'name': 'Ceguera total', 'discipline': disciplines['Carreras']},
            {'code': 'T12', 'name': 'Baja vision severa', 'discipline': disciplines['Carreras']},
            {'code': 'T13', 'name': 'Baja vision moderada', 'discipline': disciplines['Carreras']},
            {'code': 'T20', 'name': 'Discapacidad intelectual', 'discipline': disciplines['Carreras']},
            {'code': 'T33', 'name': 'Coordinacion limitada (silla)', 'discipline': disciplines['Carreras']},
            {'code': 'T34', 'name': 'Coordinacion limitada (silla)', 'discipline': disciplines['Carreras']},
            {'code': 'T35', 'name': 'Coordinacion limitada (de pie)', 'discipline': disciplines['Carreras']},
            {'code': 'T36', 'name': 'Coordinacion limitada (de pie)', 'discipline': disciplines['Carreras']},
            {'code': 'T37', 'name': 'Coordinacion limitada (de pie)', 'discipline': disciplines['Carreras']},
            {'code': 'T38', 'name': 'Coordinacion limitada (de pie)', 'discipline': disciplines['Carreras']},
            {'code': 'T42', 'name': 'Amputacion miembros inferiores', 'discipline': disciplines['Carreras']},
            {'code': 'T43', 'name': 'Amputacion doble miembros inferiores', 'discipline': disciplines['Carreras']},
            {'code': 'T44', 'name': 'Amputacion miembros inferiores', 'discipline': disciplines['Carreras']},
            {'code': 'T45', 'name': 'Amputacion miembros superiores', 'discipline': disciplines['Carreras']},
            {'code': 'T46', 'name': 'Amputacion miembros superiores', 'discipline': disciplines['Carreras']},
            {'code': 'T47', 'name': 'Amputacion miembros superiores', 'discipline': disciplines['Carreras']},
            {'code': 'T51', 'name': 'Silla de ruedas (limitado)', 'discipline': disciplines['Carreras']},
            {'code': 'T52', 'name': 'Silla de ruedas', 'discipline': disciplines['Carreras']},
            {'code': 'T53', 'name': 'Silla de ruedas', 'discipline': disciplines['Carreras']},
            {'code': 'T54', 'name': 'Silla de ruedas', 'discipline': disciplines['Carreras']},
            {'code': 'F11', 'name': 'Ceguera total', 'discipline': disciplines['Lanzamientos']},
            {'code': 'F12', 'name': 'Baja vision severa', 'discipline': disciplines['Lanzamientos']},
            {'code': 'F13', 'name': 'Baja vision moderada', 'discipline': disciplines['Lanzamientos']},
            {'code': 'F20', 'name': 'Discapacidad intelectual', 'discipline': disciplines['Lanzamientos']},
            {'code': 'F32', 'name': 'Coordinacion limitada (silla)', 'discipline': disciplines['Lanzamientos']},
            {'code': 'F33', 'name': 'Coordinacion limitada (silla)', 'discipline': disciplines['Lanzamientos']},
            {'code': 'F34', 'name': 'Coordinacion limitada (silla)', 'discipline': disciplines['Lanzamientos']},
            {'code': 'F35', 'name': 'Coordinacion limitada (de pie)', 'discipline': disciplines['Lanzamientos']},
            {'code': 'F36', 'name': 'Coordinacion limitada (de pie)', 'discipline': disciplines['Lanzamientos']},
            {'code': 'F37', 'name': 'Coordinacion limitada (de pie)', 'discipline': disciplines['Lanzamientos']},
            {'code': 'F38', 'name': 'Coordinacion limitada (de pie)', 'discipline': disciplines['Lanzamientos']},
            {'code': 'F40', 'name': 'Baja talla', 'discipline': disciplines['Lanzamientos']},
            {'code': 'F41', 'name': 'Baja talla', 'discipline': disciplines['Lanzamientos']},
            {'code': 'F42', 'name': 'Amputacion miembros inferiores', 'discipline': disciplines['Lanzamientos']},
            {'code': 'F43', 'name': 'Amputacion doble miembros inferiores', 'discipline': disciplines['Lanzamientos']},
            {'code': 'F44', 'name': 'Amputacion miembros inferiores', 'discipline': disciplines['Lanzamientos']},
            {'code': 'F45', 'name': 'Amputacion miembros superiores', 'discipline': disciplines['Lanzamientos']},
            {'code': 'F46', 'name': 'Amputacion miembros superiores', 'discipline': disciplines['Lanzamientos']},
            {'code': 'F47', 'name': 'Amputacion miembros superiores', 'discipline': disciplines['Lanzamientos']},
            {'code': 'F51', 'name': 'Silla de ruedas (limitado)', 'discipline': disciplines['Lanzamientos']},
            {'code': 'F52', 'name': 'Silla de ruedas', 'discipline': disciplines['Lanzamientos']},
            {'code': 'F53', 'name': 'Silla de ruedas', 'discipline': disciplines['Lanzamientos']},
            {'code': 'F54', 'name': 'Silla de ruedas', 'discipline': disciplines['Lanzamientos']},
            {'code': 'F55', 'name': 'Silla de ruedas', 'discipline': disciplines['Lanzamientos']},
            {'code': 'F56', 'name': 'Silla de ruedas', 'discipline': disciplines['Lanzamientos']},
            {'code': 'F57', 'name': 'Silla de ruedas', 'discipline': disciplines['Lanzamientos']},
            {'code': 'F64', 'name': 'Amputacion miembros inferiores', 'discipline': disciplines['Saltos']},
        ]
        for c_data in classifications_data:
            FunctionalClassification.objects.get_or_create(
                code=c_data['code'],
                discipline=c_data['discipline'],
                defaults={'name': c_data['name']}
            )
        self.stdout.write(self.style.SUCCESS(f'{len(classifications_data)} clasificaciones creadas'))

        self.stdout.write('Creando tipos de pruebas...')
        event_types_data = [
            {'name': '100m planos', 'discipline': disciplines['Carreras'], 'is_time_based': True, 'is_distance_based': False, 'unit': 'segundos'},
            {'name': '200m planos', 'discipline': disciplines['Carreras'], 'is_time_based': True, 'is_distance_based': False, 'unit': 'segundos'},
            {'name': '400m planos', 'discipline': disciplines['Carreras'], 'is_time_based': True, 'is_distance_based': False, 'unit': 'segundos'},
            {'name': '800m planos', 'discipline': disciplines['Carreras'], 'is_time_based': True, 'is_distance_based': False, 'unit': 'segundos'},
            {'name': '1500m planos', 'discipline': disciplines['Carreras'], 'is_time_based': True, 'is_distance_based': False, 'unit': 'segundos'},
            {'name': '5000m planos', 'discipline': disciplines['Carreras'], 'is_time_based': True, 'is_distance_based': False, 'unit': 'segundos'},
            {'name': 'Relevo 4x100m', 'discipline': disciplines['Carreras'], 'is_time_based': True, 'is_distance_based': False, 'unit': 'segundos'},
            {'name': 'Relevo 4x400m', 'discipline': disciplines['Carreras'], 'is_time_based': True, 'is_distance_based': False, 'unit': 'segundos'},
            {'name': 'Salto en longitud', 'discipline': disciplines['Saltos'], 'is_time_based': False, 'is_distance_based': True, 'unit': 'metros'},
            {'name': 'Salto en altura', 'discipline': disciplines['Saltos'], 'is_time_based': False, 'is_distance_based': True, 'unit': 'metros'},
            {'name': 'Triple salto', 'discipline': disciplines['Saltos'], 'is_time_based': False, 'is_distance_based': True, 'unit': 'metros'},
            {'name': 'Lanzamiento de bala', 'discipline': disciplines['Lanzamientos'], 'is_time_based': False, 'is_distance_based': True, 'unit': 'metros'},
            {'name': 'Lanzamiento de disco', 'discipline': disciplines['Lanzamientos'], 'is_time_based': False, 'is_distance_based': True, 'unit': 'metros'},
            {'name': 'Lanzamiento de jabalina', 'discipline': disciplines['Lanzamientos'], 'is_time_based': False, 'is_distance_based': True, 'unit': 'metros'},
            {'name': 'Lanzamiento de maza', 'discipline': disciplines['Lanzamientos'], 'is_time_based': False, 'is_distance_based': True, 'unit': 'metros'},
        ]
        for et_data in event_types_data:
            EventType.objects.get_or_create(
                name=et_data['name'],
                discipline=et_data['discipline'],
                defaults={
                    'is_time_based': et_data['is_time_based'],
                    'is_distance_based': et_data['is_distance_based'],
                    'unit': et_data['unit'],
                }
            )
        self.stdout.write(self.style.SUCCESS(f'{len(event_types_data)} tipos de pruebas creados'))

        self.stdout.write(self.style.SUCCESS('Datos iniciales cargados correctamente'))
