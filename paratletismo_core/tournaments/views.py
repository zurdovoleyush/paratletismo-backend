from rest_framework import generics, status, permissions
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q, Count as ModelsCount
from .models import Institution, InstitutionUser, Coach, Athlete, Tournament, TournamentEvent, OrganizationPayment
from .serializers import (
    InstitutionSerializer, InstitutionCreateSerializer, InstitutionManageSerializer,
    InstitutionUserSerializer, OrganizationPaymentSerializer,
    CoachSerializer, CoachCreateSerializer, AthleteSerializer, AthleteCreateSerializer, AthleteUpdateSerializer,
    TournamentSerializer, TournamentCreateSerializer, TournamentEventSerializer, TournamentEventBulkCreateSerializer,
    InstitutionTournamentSerializer
)
from paratletismo_core.users.models import RoleChoices
from paratletismo_core.users.permissions import IsSuperAdmin, CanOrganizeTournament


def can_manage_tournament(user, tournament):
    """Tiene control sobre el torneo: su creador, un superadmin o un miembro de la institucion organizadora."""
    if user is None or not user.is_authenticated:
        return False
    if getattr(user, 'is_superuser', False) or tournament.admin_user_id == user.id:
        return True
    return InstitutionUser.objects.filter(user=user, institution_id=tournament.organizer_id).exists()


class InstitutionListView(generics.ListCreateAPIView):

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return InstitutionCreateSerializer
        return InstitutionSerializer

    def get_queryset(self):
        return Institution.objects.all()

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        user = self.request.user
        data = {}
        if not serializer.validated_data.get('name'):
            data['name'] = user.first_name or user.email.split('@')[0]
        if not serializer.validated_data.get('short_name'):
            data['short_name'] = user.last_name or ''
        instance = serializer.save(**data)
        InstitutionUser.objects.create(
            institution=instance,
            user=user,
            position='Administrador'
        )

        try:
            institution_name = instance.name
            recipient = instance.email or user.email
            if recipient:
                send_mail(
                    subject=f'Bienvenido a Paratletismo - {institution_name}',
                    message=(
                        f'Hola,\n\n'
                        f'Su institucion "{institution_name}" se ha registrado correctamente en la plataforma de Paratletismo.\n\n'
                        f'PROXIMOS PASOS:\n\n'
                        f'1. COMPLETAR EL PERFIL: Ingrese a su panel y complete los datos de la institucion '
                        f'(direccion, telefono, descripcion, etc.).\n\n'
                        f'2. CARGAR ENTRENADORES Y ATLETAS: Puede comenzar a registrar entrenadores y atletas '
                        f'de su institucion desde el panel de control.\n\n'
                        f'3. HABILITACION PARA ORGANIZAR TORNEOS: Para poder crear y organizar torneos, '
                        f'su institucion necesita ser habilitada por el administrador del sistema. '
                        f'Una vez que su perfil este completo, el administrador revisara su solicitud '
                        f'y le habilitara el acceso para organizar eventos deportivos.\n\n'
                        f'Mientras tanto, puede:\n'
                        f'  - Ver torneos disponibles en la seccion publica\n'
                        f'  - Inscribir atletas en torneos abiertos\n'
                        f'  - Gestionar el perfil de su institucion\n\n'
                        f'Si tiene consultas, comuniquese con el administrador del sistema.\n\n'
                        f'Saludos,\n'
                        f'Equipo de Paratletismo'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient],
                    fail_silently=True,
                )
        except Exception:
            pass


class InstitutionDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = InstitutionSerializer

    def get_queryset(self):
        return Institution.objects.all()

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]


class InstitutionAthletesView(generics.ListAPIView):
    serializer_class = AthleteSerializer

    def get_queryset(self):
        return Athlete.objects.filter(institution_id=self.kwargs['pk']).select_related('user', 'sex', 'functional_classification')

    def get_permissions(self):
        return [permissions.IsAuthenticated()]


class InstitutionCoachesView(generics.ListAPIView):
    serializer_class = CoachSerializer

    def get_queryset(self):
        return Coach.objects.filter(institution_id=self.kwargs['pk']).select_related('user')

    def get_permissions(self):
        return [permissions.IsAuthenticated()]


class InstitutionTournamentsView(generics.ListAPIView):
    """Torneos organizados por la institucion (incluye los finalizados) con sus pruebas cargadas."""
    serializer_class = InstitutionTournamentSerializer
    pagination_class = None

    def get_queryset(self):
        institution = self.get_object()
        return Tournament.objects.filter(organizer=institution).prefetch_related(
            'disciplines', 'sexes', 'categories', 'functional_classifications', 'events'
        ).order_by('-tournament_start')

    def get_object(self):
        try:
            return Institution.objects.get(id=self.kwargs['pk'])
        except Institution.DoesNotExist:
            raise NotFound('Institucion no encontrada')

    def get_permissions(self):
        return [permissions.IsAuthenticated()]

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        user = request.user
        if user.is_superuser:
            return None
        if InstitutionUser.objects.filter(user=user, institution=obj).exists():
            return None
        raise PermissionDenied('No tenes permisos para ver los torneos de esta institucion')


class CoachListView(generics.ListCreateAPIView):
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CoachCreateSerializer
        return CoachSerializer

    def get_queryset(self):
        qs = Coach.objects.select_related('user')
        institution = self.request.query_params.get('institution')
        if institution:
            qs = qs.filter(institution_id=institution)
        return qs

    def get_permissions(self):
        return [permissions.IsAuthenticated()]


class CoachDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CoachSerializer
    queryset = Coach.objects.select_related('user')

    def get_permissions(self):
        return [permissions.IsAuthenticated()]


class AthleteListView(generics.ListCreateAPIView):
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AthleteCreateSerializer
        return AthleteSerializer

    def get_queryset(self):
        qs = Athlete.objects.select_related('user', 'institution', 'coach')
        institution = self.request.query_params.get('institution')
        coach = self.request.query_params.get('coach')
        if institution:
            qs = qs.filter(institution_id=institution)
        if coach:
            qs = qs.filter(coach_id=coach)
        return qs

    def get_permissions(self):
        return [permissions.IsAuthenticated()]


class AthleteDetailView(generics.RetrieveUpdateDestroyAPIView):
    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return AthleteUpdateSerializer
        return AthleteSerializer

    def get_queryset(self):
        return Athlete.objects.select_related('user', 'institution', 'coach')

    def get_permissions(self):
        return [permissions.IsAuthenticated()]


class TournamentListView(generics.ListCreateAPIView):
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TournamentCreateSerializer
        return TournamentSerializer

    def get_queryset(self):
        from paratletismo_core.competitions.models import FinalResult, Result
        qs = Tournament.objects.prefetch_related('disciplines', 'sexes', 'categories', 'functional_classifications').annotate(
            marks_count=(
                ModelsCount('events__final_results', distinct=True)
                + ModelsCount('events__athlete_events__results', distinct=True)
            )
        )
        user = self.request.user
        if user is None or not user.is_authenticated:
            qs = qs.filter(payment_status='paid', is_active=True)
        elif user.role not in (RoleChoices.SUPERADMIN, RoleChoices.ADMIN):
            qs = qs.filter(Q(payment_status='paid', is_active=True) | Q(admin_user=user))
        payment_status = self.request.query_params.get('payment_status')
        if payment_status:
            qs = qs.filter(payment_status=payment_status)
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)
        admin_user = self.request.query_params.get('admin_user')
        if admin_user:
            qs = qs.filter(admin_user_id=admin_user)
        return qs.order_by('-tournament_start')

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), CanOrganizeTournament()]


class TournamentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TournamentSerializer

    def get_queryset(self):
        from paratletismo_core.competitions.models import FinalResult, Result
        qs = Tournament.objects.prefetch_related('disciplines', 'sexes', 'categories', 'functional_classifications').annotate(
            marks_count=(
                ModelsCount('events__final_results', distinct=True)
                + ModelsCount('events__athlete_events__results', distinct=True)
            )
        )
        if self.request.method == 'GET':
            user = self.request.user
            if user is not None and user.is_authenticated and user.role in (RoleChoices.SUPERADMIN, RoleChoices.ADMIN):
                return qs
            if user is not None and user.is_authenticated:
                return qs.filter(Q(payment_status='paid', is_active=True) | Q(admin_user=user))
            return qs.filter(payment_status='paid', is_active=True)
        return qs

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def update(self, request, *args, **kwargs):
        tournament = self.get_object()
        if not can_manage_tournament(request.user, tournament):
            return Response({'error': 'No tenes permisos para editar este torneo'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        tournament = self.get_object()
        is_super = bool(getattr(request.user, 'is_superuser', False))
        if not can_manage_tournament(request.user, tournament) and not is_super:
            return Response({'error': 'No tenes permisos para eliminar este torneo'}, status=status.HTTP_403_FORBIDDEN)
        from paratletismo_core.competitions.models import FinalResult, Result
        has_marks = (
            FinalResult.objects.filter(tournament_event__tournament=tournament).exists()
            or Result.objects.filter(athlete_event__tournament_event__tournament=tournament).exists()
        )
        if has_marks and not is_super:
            return Response(
                {'error': 'Este torneo tiene marcas cargadas y no puede eliminarse. Podes marcarlo como Inactivo en su perfil para ocultarlo, las marcas de los atletas se conservan.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if has_marks:
            tournament.delete()
            return Response(
                {'message': 'Torneo eliminado por el superadministrador. Se eliminaron sus marcas, resultados, inscripciones y pruebas.', 'force': True},
                status=status.HTTP_200_OK
            )
        return super().destroy(request, *args, **kwargs)


class TournamentEventScheduleView(generics.UpdateAPIView):
    queryset = TournamentEvent.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def update(self, request, *args, **kwargs):
        event = self.get_object()
        if not can_manage_tournament(request.user, event.tournament):
            return Response({'error': 'No tenes permisos para programar esta prueba'}, status=status.HTTP_403_FORBIDDEN)
        event.scheduled_date = request.data.get('scheduled_date', event.scheduled_date)
        event.scheduled_time = request.data.get('scheduled_time', event.scheduled_time)
        event.venue_detail = request.data.get('venue_detail', event.venue_detail)
        event.save()
        return Response(TournamentEventSerializer(event).data)


class TournamentBulkScheduleView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        tournament_id = kwargs.get('pk')
        try:
            tournament = Tournament.objects.get(id=tournament_id)
        except Tournament.DoesNotExist:
            return Response({'error': 'Torneo no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        if not can_manage_tournament(request.user, tournament):
            return Response({'error': 'No tenes permisos para programar'}, status=status.HTTP_403_FORBIDDEN)

        schedules = request.data.get('schedules', [])
        updated = []
        for s in schedules:
            try:
                event = TournamentEvent.objects.get(id=s.get('event_id'), tournament_id=tournament_id)
            except TournamentEvent.DoesNotExist:
                continue
            if s.get('scheduled_date'):
                event.scheduled_date = s.get('scheduled_date')
            if 'scheduled_time' in s:
                from datetime import time
                if s.get('scheduled_time'):
                    event.scheduled_time = time.fromisoformat(s['scheduled_time']) if isinstance(s['scheduled_time'], str) else s['scheduled_time']
                else:
                    event.scheduled_time = None
            if 'call_time' in s:
                from datetime import time
                if s.get('call_time'):
                    event.call_time = time.fromisoformat(s['call_time']) if isinstance(s['call_time'], str) else s['call_time']
                else:
                    event.call_time = None
            if 'venue_detail' in s:
                event.venue_detail = s.get('venue_detail', '')
            event.save()
            updated.append(TournamentEventSerializer(event).data)
        return Response({'updated': len(updated), 'events': updated})


class TournamentUpdateStatusView(generics.UpdateAPIView):
    serializer_class = TournamentSerializer
    queryset = Tournament.objects.all()

    def update(self, request, *args, **kwargs):
        tournament = self.get_object()
        if not can_manage_tournament(request.user, tournament):
            return Response({'error': 'No tenes permisos para cambiar el estado de este torneo'}, status=status.HTTP_403_FORBIDDEN)
        new_status = request.data.get('status')
        if new_status not in dict(Tournament.STATUS_CHOICES):
            return Response({'error': 'Estado invalido'}, status=status.HTTP_400_BAD_REQUEST)
        if (tournament.payment_status == 'pending'
                and new_status != 'draft'
                and request.user.role not in (RoleChoices.SUPERADMIN, RoleChoices.ADMIN)):
            return Response(
                {'error': 'El torneo esta pendiente de pago. Debe ser habilitado por el administrador para abrir la inscripcion.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        tournament.status = new_status
        tournament.save()
        return Response(TournamentSerializer(tournament).data)


class TournamentPaymentView(generics.UpdateAPIView):
    """Superadmin: habilitar un torneo tras registrar el pago del servicio."""
    serializer_class = TournamentSerializer
    queryset = Tournament.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def update(self, request, *args, **kwargs):
        tournament = self.get_object()
        payment_status = request.data.get('status', 'paid')
        if payment_status not in ('paid', 'pending'):
            return Response({'error': 'Estado de pago invalido'}, status=status.HTTP_400_BAD_REQUEST)
        from datetime import datetime, timezone
        if payment_status == 'paid':
            tournament.payment_status = 'paid'
            tournament.payment_amount = request.data.get('amount') or tournament.payment_amount
            tournament.payment_notes = request.data.get('notes') or ''
            tournament.payment_date = datetime.now(timezone.utc)
            tournament.paid_by = request.user
        else:
            tournament.payment_status = 'pending'
            tournament.payment_amount = None
            tournament.payment_notes = ''
            tournament.payment_date = None
            tournament.paid_by = None
            tournament.status = 'draft'
        tournament.save()
        return Response(TournamentSerializer(tournament).data)


class TournamentEventsView(generics.ListCreateAPIView):
    serializer_class = TournamentEventSerializer
    pagination_class = None

    def get_queryset(self):
        from django.db.models import Count
        qs = TournamentEvent.objects.filter(tournament_id=self.kwargs['pk']).annotate(
            athlete_count=Count('athlete_events', distinct=True)
        )
        has_athletes = self.request.query_params.get('has_athletes')
        if has_athletes == 'true':
            from paratletismo_core.competitions.models import AthleteEvent
            event_ids = AthleteEvent.objects.filter(
                tournament_event__tournament_id=self.kwargs['pk']
            ).values_list('tournament_event_id', flat=True).distinct()
            qs = qs.filter(id__in=event_ids)
        return qs

    def get_permissions(self):
        return [permissions.IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        tournament = Tournament.objects.get(id=self.kwargs['pk'])
        if not can_manage_tournament(request.user, tournament):
            return Response({'error': 'No tenes permisos para gestionar pruebas de este torneo'}, status=status.HTTP_403_FORBIDDEN)
        if 'event_types' in request.data or 'groups' in request.data or 'combos' in request.data:
            serializer = TournamentEventBulkCreateSerializer(
                data={**request.data, 'tournament': self.kwargs['pk']},
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            events = serializer.save()
            return Response(
                {'message': f'{len(events)} pruebas creadas', 'count': len(events)},
                status=status.HTTP_201_CREATED
            )
        return super().create(request, *args, **kwargs)


class TournamentFinalizeEventsView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        tournament_id = kwargs.get('pk')
        try:
            tournament = Tournament.objects.get(id=tournament_id)
        except Tournament.DoesNotExist:
            return Response({'error': 'Torneo no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        if not can_manage_tournament(request.user, tournament):
            return Response({'error': 'No tenes permisos para oficializar las pruebas de este torneo'}, status=status.HTTP_403_FORBIDDEN)
        if tournament.status not in ['registration_closed', 'in_progress']:
            return Response({'error': 'La inscripcion debe estar cerrada para oficializar las pruebas'}, status=status.HTTP_400_BAD_REQUEST)

        from paratletismo_core.competitions.models import AthleteEvent

        events = TournamentEvent.objects.filter(tournament=tournament).prefetch_related('athlete_events')
        officialized = []
        deleted = []
        for event in events:
            if AthleteEvent.objects.filter(tournament_event=event).exists():
                event.is_final = True
                event.save()
                officialized.append(TournamentEventSerializer(event).data)
            else:
                deleted.append({'id': str(event.id), 'name': event.name})
                event.delete()

        return Response({
            'message': f'{len(officialized)} pruebas oficializadas, {len(deleted)} pruebas sin inscriptos eliminadas',
            'officialized': officialized,
            'deleted': deleted,
        }, status=status.HTTP_200_OK)


class TournamentEventDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TournamentEventSerializer
    queryset = TournamentEvent.objects.all()

    def get_permissions(self):
        return [permissions.IsAuthenticated()]


class MyInstitutionView(generics.RetrieveAPIView):
    serializer_class = InstitutionSerializer

    def get_object(self):
        user = self.request.user
        try:
            return InstitutionUser.objects.get(user=user).institution
        except InstitutionUser.DoesNotExist:
            pass
        if user.role == RoleChoices.COACH:
            try:
                coach = Coach.objects.get(user=user)
                if coach.institution:
                    return coach.institution
            except Coach.DoesNotExist:
                pass
        raise NotFound("No tienes una institucion vinculada")


class AvailableInstitutionsView(generics.ListAPIView):
    serializer_class = InstitutionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Institution.objects.filter(is_active=True)


class CoachSetInstitutionView(generics.UpdateAPIView):
    serializer_class = CoachSerializer
    permission_classes = [permissions.IsAuthenticated]

    def update(self, request, *args, **kwargs):
        coach = Coach.objects.get(user=request.user)
        institution_id = request.data.get('institution')
        if not institution_id:
            return Response({'error': 'institution es obligatorio'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            institution = Institution.objects.get(id=institution_id)
            coach.institution = institution
            coach.save()
            return Response(CoachSerializer(coach).data)
        except Institution.DoesNotExist:
            return Response({'error': 'Institucion no encontrada'}, status=status.HTTP_404_NOT_FOUND)


class MyAthletesView(generics.ListAPIView):
    serializer_class = AthleteSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == RoleChoices.COACH:
            coach = Coach.objects.get(user=user)
            return Athlete.objects.filter(coach=coach).select_related('user', 'sex', 'functional_classification')
        elif user.role == RoleChoices.INSTITUTION:
            institution = InstitutionUser.objects.get(user=user).institution
            return Athlete.objects.filter(institution=institution).select_related('user', 'sex', 'functional_classification')
        return Athlete.objects.none()


class MyAthleteProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = AthleteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        user = self.request.user
        if user.role != RoleChoices.ATHLETE:
            raise PermissionDenied("Este perfil solo está disponible para atletas")
        athlete, created = Athlete.objects.get_or_create(user=user)
        return athlete


class InstitutionManageView(generics.ListAPIView):
    """Superadmin: listar todas las instituciones con permisos de organizador."""
    serializer_class = InstitutionManageSerializer
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def get_queryset(self):
        qs = Institution.objects.all().order_by('name')
        show_all = self.request.query_params.get('show_all', '').lower() in ('true', '1', 'yes')
        if not show_all:
            qs = qs.filter(is_active=True)
        return qs


class InstitutionToggleOrganizeView(generics.UpdateAPIView):
    """Superadmin: activar/desactivar permiso de organizar torneos para una institucion."""
    serializer_class = InstitutionManageSerializer
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]
    queryset = Institution.objects.all()

    def update(self, request, *args, **kwargs):
        institution = self.get_object()
        is_active = request.data.get('is_active')
        if is_active is not None:
            institution.is_active = bool(is_active)
        can_organize = request.data.get('can_organize')
        if can_organize is not None:
            institution.can_organize = bool(can_organize)
        organized_until = request.data.get('organized_until')
        if organized_until is not None:
            from datetime import date
            try:
                institution.organized_until = date.fromisoformat(organized_until) if isinstance(organized_until, str) else organized_until
            except (ValueError, TypeError):
                return Response({'error': 'Fecha invalida. Use formato YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
        elif not institution.can_organize:
            institution.organized_until = None
        fields = []
        if 'is_active' in request.data:
            fields.append('is_active')
        if 'can_organize' in request.data:
            fields.append('can_organize')
        if 'organized_until' in request.data:
            fields.append('organized_until')
        if not fields:
            return Response(InstitutionManageSerializer(institution).data)
        institution.save(update_fields=fields)
        return Response(InstitutionManageSerializer(institution).data)


class OrganizationPaymentListView(generics.ListCreateAPIView):
    """Superadmin: listar y registrar pagos de organizacion."""
    serializer_class = OrganizationPaymentSerializer
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def get_queryset(self):
        qs = OrganizationPayment.objects.select_related('institution', 'paid_by').all()
        institution = self.request.query_params.get('institution')
        if institution:
            qs = qs.filter(institution_id=institution)
        return qs

    def perform_create(self, serializer):
        serializer.save(paid_by=self.request.user)


class TournamentStartListView(generics.RetrieveAPIView):
    """Genera el PDF de Start List con todas las pruebas oficiales del torneo."""
    queryset = Tournament.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        from paratletismo_core.competitions.pdf import build_tournament_start_list_pdf
        from django.http import HttpResponse
        import re
        tournament = self.get_object()
        pdf_bytes = build_tournament_start_list_pdf(tournament)
        if pdf_bytes is None:
            return Response(
                {'error': 'No hay pruebas oficiales con atletas inscriptos para generar el Start List'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        safe = re.sub(r'[^A-Za-z0-9]+', '_', tournament.name).strip('_') or 'torneo'
        filename = f'start_list_{safe}.pdf'
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
